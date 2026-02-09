from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
import json
import math
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Tuple

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


@dataclass
class ResourceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    memory_available_mb: float
    swap_percent: float
    gpu_util_percent: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None


@dataclass
class TaskSpec:
    task_id: str
    command: List[str]
    priority: int
    estimated_mem_mb: int
    estimated_cpu_percent: float
    estimated_gpu_mem_mb: int = 0
    preemptible: bool = True
    max_runtime_sec: float = 300.0
    dry_run_ticks: int = 2


@dataclass
class SchedulerConfig:
    max_workers: int = 4
    min_workers: int = 1
    check_interval_sec: float = 0.5

    memory_high_pct: float = 85.0
    memory_emergency_pct: float = 92.0
    cpu_high_pct: float = 80.0
    cpu_hard_pct: float = 95.0
    swap_emergency_pct: float = 80.0

    enable_gpu_guard: bool = True
    gpu_memory_high_pct: float = 85.0
    gpu_memory_emergency_pct: float = 95.0

    reserve_memory_mb: int = 512
    high_mode_priority_cutoff: int = 3
    preempt_count_per_tick: int = 1
    kill_timeout_sec: float = 3.0

    dry_run: bool = False


@dataclass
class TaskRuntime:
    spec: TaskSpec
    start_ts: float
    state: str
    process: Optional[subprocess.Popen] = None
    remaining_ticks: int = 0


@dataclass
class SchedulerMetrics:
    submitted_total: int = 0
    started_total: int = 0
    completed_total: int = 0
    blocked_total: int = 0
    preempted_total: int = 0
    failed_total: int = 0
    timeout_total: int = 0
    emergency_ticks: int = 0


@dataclass
class TickReport:
    tick_id: int
    mode: str
    started: List[str]
    blocked: List[Dict[str, str]]
    preempted: List[str]
    running_count: int
    pending_count: int
    snapshot: ResourceSnapshot


class ResourceMonitor:
    """采样本机 CPU/内存/GPU。GPU 通过 nvidia-smi（若可用）。"""

    def __init__(self, enable_gpu: bool = True) -> None:
        self.enable_gpu = enable_gpu

    def sample(self) -> ResourceSnapshot:
        ts = time.time()
        cpu_percent = 10.0
        memory_percent = 35.0
        memory_total_mb = 16 * 1024.0
        memory_available_mb = 10 * 1024.0
        memory_used_mb = memory_total_mb - memory_available_mb
        swap_percent = 5.0

        if psutil is not None:
            cpu_percent = float(psutil.cpu_percent(interval=None))
            vm = psutil.virtual_memory()
            sm = psutil.swap_memory()
            memory_percent = float(vm.percent)
            memory_total_mb = float(vm.total / (1024 * 1024))
            memory_available_mb = float(vm.available / (1024 * 1024))
            memory_used_mb = float(vm.used / (1024 * 1024))
            swap_percent = float(sm.percent)

        gpu = self._sample_gpu() if self.enable_gpu else {}
        return ResourceSnapshot(
            timestamp=ts,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_total_mb=memory_total_mb,
            memory_available_mb=memory_available_mb,
            swap_percent=swap_percent,
            gpu_util_percent=gpu.get("gpu_util_percent"),
            gpu_memory_percent=gpu.get("gpu_memory_percent"),
            gpu_memory_used_mb=gpu.get("gpu_memory_used_mb"),
            gpu_memory_total_mb=gpu.get("gpu_memory_total_mb"),
        )

    def _sample_gpu(self) -> Dict[str, float]:
        if shutil.which("nvidia-smi") is None:
            return {}
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=1.5,
            )
            line = out.strip().splitlines()[0]
            util_s, used_s, total_s = [x.strip() for x in line.split(",")]
            util = float(util_s)
            used_mb = float(used_s)
            total_mb = max(1.0, float(total_s))
            mem_pct = 100.0 * used_mb / total_mb
            return {
                "gpu_util_percent": util,
                "gpu_memory_percent": mem_pct,
                "gpu_memory_used_mb": used_mb,
                "gpu_memory_total_mb": total_mb,
            }
        except Exception:
            return {}


class DynamicTaskScheduler:
    def __init__(self, config: SchedulerConfig, monitor: Optional[ResourceMonitor] = None) -> None:
        self.config = config
        self.monitor = monitor or ResourceMonitor(enable_gpu=config.enable_gpu_guard)

        self.pending: List[Tuple[int, int, TaskSpec]] = []
        self.running: Dict[str, TaskRuntime] = {}
        self.metrics = SchedulerMetrics()

        self._seq = 0
        self._tick_id = 0
        self.events: List[Dict[str, object]] = []

    def submit_task(self, task: TaskSpec) -> None:
        self._seq += 1
        heapq.heappush(self.pending, (task.priority, self._seq, task))
        self.metrics.submitted_total += 1
        self._event("TASK_SUBMITTED", {"task_id": task.task_id, "priority": task.priority})

    def tick(self) -> TickReport:
        self._tick_id += 1
        self._refresh_running()

        snapshot = self.monitor.sample()
        mode = self._evaluate_mode(snapshot)
        if mode == "EMERGENCY":
            self.metrics.emergency_ticks += 1

        preempted: List[str] = []
        if mode == "EMERGENCY":
            preempted = self._preempt_low_priority()

        target_workers = self._compute_target_workers(mode)
        started: List[str] = []
        blocked: List[Dict[str, str]] = []

        if target_workers > len(self.running) and self.pending:
            attempts = len(self.pending)
            blocked_tasks: List[Tuple[TaskSpec, str]] = []
            for _ in range(attempts):
                if len(self.running) >= target_workers or not self.pending:
                    break
                _, _, task = heapq.heappop(self.pending)
                ok, reason = self._can_admit(task, snapshot, mode)
                if ok:
                    self._start_task(task)
                    started.append(task.task_id)
                else:
                    self.metrics.blocked_total += 1
                    blocked.append({"task_id": task.task_id, "reason": reason})
                    blocked_tasks.append((task, reason))
                    self._event("TASK_BLOCKED", {"task_id": task.task_id, "reason": reason})

            for task, _ in blocked_tasks:
                self._seq += 1
                heapq.heappush(self.pending, (task.priority, self._seq, task))

        report = TickReport(
            tick_id=self._tick_id,
            mode=mode,
            started=started,
            blocked=blocked,
            preempted=preempted,
            running_count=len(self.running),
            pending_count=len(self.pending),
            snapshot=snapshot,
        )
        self._event("TICK", asdict(report))
        return report

    def shutdown(self) -> None:
        for task_id in list(self.running.keys()):
            self._stop_task(task_id, "SHUTDOWN")

    def metrics_dict(self) -> Dict[str, int]:
        return asdict(self.metrics)

    def dump_events_json(self) -> str:
        return json.dumps(self.events, ensure_ascii=False, indent=2)

    def _evaluate_mode(self, s: ResourceSnapshot) -> str:
        if s.memory_percent >= self.config.memory_emergency_pct:
            return "EMERGENCY"
        if s.swap_percent >= self.config.swap_emergency_pct:
            return "EMERGENCY"
        if (
            self.config.enable_gpu_guard
            and s.gpu_memory_percent is not None
            and s.gpu_memory_percent >= self.config.gpu_memory_emergency_pct
        ):
            return "EMERGENCY"

        if s.memory_percent >= self.config.memory_high_pct:
            return "HIGH"
        if s.cpu_percent >= self.config.cpu_high_pct:
            return "HIGH"
        if (
            self.config.enable_gpu_guard
            and s.gpu_memory_percent is not None
            and s.gpu_memory_percent >= self.config.gpu_memory_high_pct
        ):
            return "HIGH"

        return "NORMAL"

    def _compute_target_workers(self, mode: str) -> int:
        if mode == "NORMAL":
            return self.config.max_workers
        if mode == "HIGH":
            return max(self.config.min_workers, self.config.max_workers // 2)
        return 0

    def _can_admit(self, task: TaskSpec, s: ResourceSnapshot, mode: str) -> Tuple[bool, str]:
        if mode == "EMERGENCY":
            return False, "emergency mode"

        projected_mem_mb = s.memory_used_mb + task.estimated_mem_mb + self.config.reserve_memory_mb
        projected_mem_pct = 100.0 * projected_mem_mb / max(1.0, s.memory_total_mb)
        if projected_mem_pct >= self.config.memory_emergency_pct:
            return False, "projected memory emergency"

        projected_cpu_pct = s.cpu_percent + task.estimated_cpu_percent
        if projected_cpu_pct >= self.config.cpu_hard_pct:
            return False, "projected cpu hard limit"

        if mode == "HIGH" and task.priority > self.config.high_mode_priority_cutoff:
            return False, "high mode blocks low-priority task"

        if (
            self.config.enable_gpu_guard
            and s.gpu_memory_total_mb is not None
            and s.gpu_memory_used_mb is not None
            and task.estimated_gpu_mem_mb > 0
        ):
            projected_gpu_mb = s.gpu_memory_used_mb + task.estimated_gpu_mem_mb
            projected_gpu_pct = 100.0 * projected_gpu_mb / max(1.0, s.gpu_memory_total_mb)
            if projected_gpu_pct >= self.config.gpu_memory_emergency_pct:
                return False, "projected gpu memory emergency"

        return True, ""

    def _start_task(self, task: TaskSpec) -> None:
        now = time.time()
        if self.config.dry_run:
            runtime = TaskRuntime(
                spec=task,
                start_ts=now,
                state="RUNNING",
                process=None,
                remaining_ticks=max(1, task.dry_run_ticks),
            )
        else:
            if not task.command:
                raise ValueError(f"Task {task.task_id} has empty command.")
            process = subprocess.Popen(task.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            runtime = TaskRuntime(spec=task, start_ts=now, state="RUNNING", process=process)

        self.running[task.task_id] = runtime
        self.metrics.started_total += 1
        self._event("TASK_STARTED", {"task_id": task.task_id})

    def _refresh_running(self) -> None:
        now = time.time()
        for task_id in list(self.running.keys()):
            runtime = self.running[task_id]

            if self.config.dry_run:
                runtime.remaining_ticks -= 1
                if runtime.remaining_ticks <= 0:
                    self._finish_task(task_id, "COMPLETED")
                continue

            if runtime.process is None:
                self._finish_task(task_id, "FAILED")
                continue

            ret = runtime.process.poll()
            if ret is not None:
                if ret == 0:
                    self._finish_task(task_id, "COMPLETED")
                else:
                    self._finish_task(task_id, "FAILED")
                continue

            if (now - runtime.start_ts) > runtime.spec.max_runtime_sec:
                self.metrics.timeout_total += 1
                self._stop_task(task_id, "TIMEOUT")

    def _finish_task(self, task_id: str, state: str) -> None:
        runtime = self.running.pop(task_id, None)
        if runtime is None:
            return
        runtime.state = state
        if state == "COMPLETED":
            self.metrics.completed_total += 1
        elif state == "FAILED":
            self.metrics.failed_total += 1
        self._event("TASK_FINISHED", {"task_id": task_id, "state": state})

    def _stop_task(self, task_id: str, reason: str) -> None:
        runtime = self.running.get(task_id)
        if runtime is None:
            return

        if runtime.process is not None:
            try:
                runtime.process.terminate()
                runtime.process.wait(timeout=self.config.kill_timeout_sec)
            except Exception:
                try:
                    runtime.process.kill()
                except Exception:
                    pass

        self.running.pop(task_id, None)
        if reason == "PREEMPTED":
            self.metrics.preempted_total += 1
        elif reason == "TIMEOUT":
            self.metrics.timeout_total += 1
        self._event("TASK_STOPPED", {"task_id": task_id, "reason": reason})

    def _preempt_low_priority(self) -> List[str]:
        if not self.running:
            return []

        candidates = [r for r in self.running.values() if r.spec.preemptible]
        candidates.sort(key=lambda r: (r.spec.priority, r.start_ts), reverse=True)
        k = min(self.config.preempt_count_per_tick, len(candidates))
        preempted: List[str] = []
        for i in range(k):
            task_id = candidates[i].spec.task_id
            self._stop_task(task_id, "PREEMPTED")
            preempted.append(task_id)
        return preempted

    def _event(self, event_type: str, payload: Dict[str, object]) -> None:
        self.events.append(
            {
                "ts": round(time.time(), 3),
                "event_type": event_type,
                "payload": payload,
            }
        )


def load_scheduler_config(path: str) -> SchedulerConfig:
    raw = json.loads(open(path, "r", encoding="utf-8").read())
    cfg = SchedulerConfig()
    for key, value in raw.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    _validate_config(cfg)
    return cfg


def _validate_config(cfg: SchedulerConfig) -> None:
    if cfg.min_workers < 1 or cfg.max_workers < cfg.min_workers:
        raise ValueError("Invalid worker range.")
    for val in [
        cfg.memory_high_pct,
        cfg.memory_emergency_pct,
        cfg.cpu_high_pct,
        cfg.cpu_hard_pct,
        cfg.swap_emergency_pct,
        cfg.gpu_memory_high_pct,
        cfg.gpu_memory_emergency_pct,
    ]:
        if not (0.0 < float(val) <= 100.0):
            raise ValueError("Thresholds must be in (0, 100].")
    if cfg.memory_high_pct >= cfg.memory_emergency_pct:
        raise ValueError("memory_high_pct must be < memory_emergency_pct.")
    if cfg.cpu_high_pct >= cfg.cpu_hard_pct:
        raise ValueError("cpu_high_pct must be < cpu_hard_pct.")
