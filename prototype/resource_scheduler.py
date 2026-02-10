from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
import json
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Set, Tuple

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
    mode_hysteresis_pct: float = 3.0
    emergency_cooldown_ticks: int = 2
    ema_alpha: float = 0.6
    max_start_per_tick_normal: int = 4
    max_start_per_tick_high: int = 1

    dry_run: bool = False
    max_event_log_entries: int = 5000


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
            rows: List[Tuple[float, float, float, float]] = []
            for line in out.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = [x.strip() for x in line.split(",")]
                if len(parts) < 3:
                    continue
                util = float(parts[0])
                used_mb = float(parts[1])
                total_mb = max(1.0, float(parts[2]))
                mem_pct = 100.0 * used_mb / total_mb
                rows.append((mem_pct, util, used_mb, total_mb))
            if not rows:
                return {}

            # With multiple GPUs, guard based on the riskiest (highest memory pct) card.
            mem_pct, util, used_mb, total_mb = max(rows, key=lambda x: x[0])
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
        self._pending_task_ids: Set[str] = set()
        self.running: Dict[str, TaskRuntime] = {}
        self.metrics = SchedulerMetrics()

        self._seq = 0
        self._tick_id = 0
        self._mode = "NORMAL"
        self._emergency_cooldown_left = 0
        self._smoothed_snapshot: Optional[ResourceSnapshot] = None
        self.events: List[Dict[str, object]] = []

    def submit_task(self, task: TaskSpec) -> None:
        self._validate_task_spec(task)
        if task.task_id in self.running or task.task_id in self._pending_task_ids:
            raise ValueError(f"Duplicate task_id in scheduler queue/running set: {task.task_id}")
        self._seq += 1
        heapq.heappush(self.pending, (task.priority, self._seq, task))
        self._pending_task_ids.add(task.task_id)
        self.metrics.submitted_total += 1
        self._event("TASK_SUBMITTED", {"task_id": task.task_id, "priority": task.priority})

    def tick(self) -> TickReport:
        self._tick_id += 1
        self._refresh_running()

        raw_snapshot = self.monitor.sample()
        snapshot = self._smooth_snapshot(raw_snapshot)
        mode = self._evaluate_mode(snapshot, raw_snapshot)
        if mode == "EMERGENCY":
            self.metrics.emergency_ticks += 1

        preempted: List[str] = []
        if mode == "EMERGENCY":
            preempted = self._preempt_low_priority(snapshot)

        target_workers = self._compute_target_workers(mode)
        started: List[str] = []
        blocked: List[Dict[str, str]] = []
        planned_extra_mem_mb = 0.0
        planned_extra_cpu_pct = 0.0
        planned_extra_gpu_mb = 0.0

        if mode == "NORMAL":
            start_budget = max(1, self.config.max_start_per_tick_normal)
        elif mode == "HIGH":
            start_budget = max(1, self.config.max_start_per_tick_high)
        else:
            start_budget = 0

        if target_workers > len(self.running) and self.pending and start_budget > 0:
            attempts = len(self.pending)
            blocked_tasks: List[Tuple[TaskSpec, str]] = []
            for _ in range(attempts):
                if len(self.running) >= target_workers or not self.pending or len(started) >= start_budget:
                    break
                _, _, task = heapq.heappop(self.pending)
                self._pending_task_ids.discard(task.task_id)
                ok, reason = self._can_admit(
                    task,
                    snapshot,
                    mode,
                    planned_extra_mem_mb=planned_extra_mem_mb,
                    planned_extra_cpu_pct=planned_extra_cpu_pct,
                    planned_extra_gpu_mb=planned_extra_gpu_mb,
                )
                if ok:
                    self._start_task(task)
                    started.append(task.task_id)
                    planned_extra_mem_mb += float(task.estimated_mem_mb)
                    planned_extra_cpu_pct += float(task.estimated_cpu_percent)
                    planned_extra_gpu_mb += float(task.estimated_gpu_mem_mb)
                else:
                    self.metrics.blocked_total += 1
                    blocked.append({"task_id": task.task_id, "reason": reason})
                    blocked_tasks.append((task, reason))
                    self._event("TASK_BLOCKED", {"task_id": task.task_id, "reason": reason})

            for task, _ in blocked_tasks:
                self._seq += 1
                heapq.heappush(self.pending, (task.priority, self._seq, task))
                self._pending_task_ids.add(task.task_id)

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
        if mode != self._mode:
            self._event("MODE_CHANGED", {"from": self._mode, "to": mode})
        self._mode = mode
        self._event("TICK", asdict(report))
        return report

    def shutdown(self) -> None:
        for task_id in list(self.running.keys()):
            self._stop_task(task_id, "SHUTDOWN")

    def metrics_dict(self) -> Dict[str, int]:
        return asdict(self.metrics)

    def dump_events_json(self) -> str:
        return json.dumps(self.events, ensure_ascii=False, indent=2)

    def _smooth_snapshot(self, raw: ResourceSnapshot) -> ResourceSnapshot:
        alpha = min(1.0, max(0.0, float(self.config.ema_alpha)))
        if self._smoothed_snapshot is None or alpha >= 1.0:
            self._smoothed_snapshot = raw
            return raw

        prev = self._smoothed_snapshot

        def blend(prev_v: float, curr_v: float) -> float:
            return alpha * curr_v + (1.0 - alpha) * prev_v

        def blend_opt(prev_v: Optional[float], curr_v: Optional[float]) -> Optional[float]:
            if prev_v is None and curr_v is None:
                return None
            if prev_v is None:
                return curr_v
            if curr_v is None:
                return prev_v
            return blend(prev_v, curr_v)

        smoothed = ResourceSnapshot(
            timestamp=raw.timestamp,
            cpu_percent=blend(prev.cpu_percent, raw.cpu_percent),
            memory_percent=blend(prev.memory_percent, raw.memory_percent),
            memory_used_mb=blend(prev.memory_used_mb, raw.memory_used_mb),
            memory_total_mb=raw.memory_total_mb,
            memory_available_mb=blend(prev.memory_available_mb, raw.memory_available_mb),
            swap_percent=blend(prev.swap_percent, raw.swap_percent),
            gpu_util_percent=blend_opt(prev.gpu_util_percent, raw.gpu_util_percent),
            gpu_memory_percent=blend_opt(prev.gpu_memory_percent, raw.gpu_memory_percent),
            gpu_memory_used_mb=blend_opt(prev.gpu_memory_used_mb, raw.gpu_memory_used_mb),
            gpu_memory_total_mb=raw.gpu_memory_total_mb or prev.gpu_memory_total_mb,
        )
        self._smoothed_snapshot = smoothed
        return smoothed

    def _running_estimated_load(self) -> Tuple[float, float, float]:
        mem = 0.0
        cpu = 0.0
        gpu = 0.0
        for runtime in self.running.values():
            mem += float(runtime.spec.estimated_mem_mb)
            cpu += float(runtime.spec.estimated_cpu_percent)
            gpu += float(runtime.spec.estimated_gpu_mem_mb)
        return mem, cpu, gpu

    def _evaluate_mode(self, s: ResourceSnapshot, raw: Optional[ResourceSnapshot] = None) -> str:
        emergency_view = raw or s
        hysteresis = max(0.0, float(self.config.mode_hysteresis_pct))
        mem_high_exit = max(0.0, self.config.memory_high_pct - hysteresis)
        cpu_high_exit = max(0.0, self.config.cpu_high_pct - hysteresis)
        gpu_high_exit = max(0.0, self.config.gpu_memory_high_pct - hysteresis)

        emergency_trigger = False
        # Emergency checks must react to raw peaks; smoothing is only for non-emergency stability.
        if emergency_view.memory_percent >= self.config.memory_emergency_pct:
            emergency_trigger = True
        if emergency_view.swap_percent >= self.config.swap_emergency_pct:
            emergency_trigger = True
        if emergency_view.memory_available_mb <= max(1, self.config.reserve_memory_mb):
            emergency_trigger = True
        if (
            self.config.enable_gpu_guard
            and emergency_view.gpu_memory_percent is not None
            and emergency_view.gpu_memory_percent >= self.config.gpu_memory_emergency_pct
        ):
            emergency_trigger = True

        if emergency_trigger:
            self._emergency_cooldown_left = max(0, int(self.config.emergency_cooldown_ticks))
            return "EMERGENCY"

        if self._mode == "EMERGENCY" and self._emergency_cooldown_left > 0:
            self._emergency_cooldown_left -= 1
            return "EMERGENCY"

        high_trigger = False
        if s.memory_percent >= self.config.memory_high_pct:
            high_trigger = True
        if s.cpu_percent >= self.config.cpu_high_pct:
            high_trigger = True
        if (
            self.config.enable_gpu_guard
            and s.gpu_memory_percent is not None
            and s.gpu_memory_percent >= self.config.gpu_memory_high_pct
        ):
            high_trigger = True

        if high_trigger:
            return "HIGH"

        if self._mode == "HIGH":
            stay_high = s.memory_percent > mem_high_exit or s.cpu_percent > cpu_high_exit
            if (
                self.config.enable_gpu_guard
                and s.gpu_memory_percent is not None
                and s.gpu_memory_percent > gpu_high_exit
            ):
                stay_high = True
            return "HIGH" if stay_high else "NORMAL"

        return "NORMAL"

    def _compute_target_workers(self, mode: str) -> int:
        if mode == "NORMAL":
            return self.config.max_workers
        if mode == "HIGH":
            return max(self.config.min_workers, self.config.max_workers // 2)
        return 0

    def _can_admit(
        self,
        task: TaskSpec,
        s: ResourceSnapshot,
        mode: str,
        planned_extra_mem_mb: float = 0.0,
        planned_extra_cpu_pct: float = 0.0,
        planned_extra_gpu_mb: float = 0.0,
    ) -> Tuple[bool, str]:
        if mode == "EMERGENCY":
            return False, "emergency mode"

        base_mem_mb = s.memory_used_mb
        base_cpu_pct = s.cpu_percent
        base_gpu_mb = 0.0
        if self.config.dry_run:
            running_mem_est, running_cpu_est, running_gpu_est = self._running_estimated_load()
            # dry_run running set already contains tasks started earlier in this tick.
            # Adding planned_extra_* again would double count.
            base_mem_mb += running_mem_est
            base_cpu_pct += running_cpu_est
            base_gpu_mb += running_gpu_est
        else:
            # In real mode, planned_extra_* represents same-tick launches not reflected in snapshot yet.
            base_mem_mb += planned_extra_mem_mb
            base_cpu_pct += planned_extra_cpu_pct
            base_gpu_mb += planned_extra_gpu_mb

        projected_mem_mb = base_mem_mb + task.estimated_mem_mb + self.config.reserve_memory_mb
        projected_mem_pct = 100.0 * projected_mem_mb / max(1.0, s.memory_total_mb)
        if projected_mem_pct >= self.config.memory_emergency_pct:
            return False, f"projected memory emergency ({projected_mem_pct:.1f}%)"

        projected_cpu_pct = base_cpu_pct + task.estimated_cpu_percent
        if projected_cpu_pct >= self.config.cpu_hard_pct:
            return False, f"projected cpu hard limit ({projected_cpu_pct:.1f}%)"

        if mode == "HIGH" and task.priority > self.config.high_mode_priority_cutoff:
            return False, "high mode blocks low-priority task"

        if (
            self.config.enable_gpu_guard
            and s.gpu_memory_total_mb is not None
            and s.gpu_memory_used_mb is not None
            and task.estimated_gpu_mem_mb > 0
        ):
            projected_gpu_mb = s.gpu_memory_used_mb + base_gpu_mb + task.estimated_gpu_mem_mb
            projected_gpu_pct = 100.0 * projected_gpu_mb / max(1.0, s.gpu_memory_total_mb)
            if projected_gpu_pct >= self.config.gpu_memory_emergency_pct:
                return False, f"projected gpu memory emergency ({projected_gpu_pct:.1f}%)"

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

    def _stop_task(self, task_id: str, reason: str) -> bool:
        runtime = self.running.get(task_id)
        if runtime is None:
            return False

        stopped = True
        if runtime.process is not None:
            try:
                runtime.process.terminate()
                runtime.process.wait(timeout=self.config.kill_timeout_sec)
            except Exception:
                try:
                    runtime.process.kill()
                    runtime.process.wait(timeout=self.config.kill_timeout_sec)
                except Exception:
                    stopped = False
            if runtime.process.poll() is None:
                stopped = False

        if not stopped:
            self._event("TASK_STOP_FAILED", {"task_id": task_id, "reason": reason})
            return False

        self.running.pop(task_id, None)
        if reason == "PREEMPTED":
            self.metrics.preempted_total += 1
        elif reason == "TIMEOUT":
            self.metrics.timeout_total += 1
        self._event("TASK_STOPPED", {"task_id": task_id, "reason": reason})
        return True

    def _preempt_low_priority(self, snapshot: ResourceSnapshot) -> List[str]:
        if not self.running:
            return []

        candidates = [r for r in self.running.values() if r.spec.preemptible]
        candidates.sort(
            key=lambda r: (r.spec.priority, r.spec.estimated_mem_mb, -r.start_ts),
            reverse=True,
        )
        k = min(self.config.preempt_count_per_tick, len(candidates))

        target_mb = (snapshot.memory_total_mb * self.config.memory_high_pct / 100.0) - self.config.reserve_memory_mb
        if self.config.dry_run:
            base_mb = snapshot.memory_used_mb + self._running_estimated_load()[0]
        else:
            base_mb = snapshot.memory_used_mb
        reclaim_needed_mb = max(0.0, base_mb - target_mb)

        preempted: List[str] = []
        reclaimed_mb = 0.0
        for i in range(k):
            task_id = candidates[i].spec.task_id
            if self._stop_task(task_id, "PREEMPTED"):
                preempted.append(task_id)
                reclaimed_mb += float(candidates[i].spec.estimated_mem_mb)
                if reclaim_needed_mb > 0 and reclaimed_mb >= reclaim_needed_mb and preempted:
                    break
        return preempted

    def _event(self, event_type: str, payload: Dict[str, object]) -> None:
        self.events.append(
            {
                "ts": round(time.time(), 3),
                "event_type": event_type,
                "payload": payload,
            }
        )
        if len(self.events) > self.config.max_event_log_entries:
            overflow = len(self.events) - self.config.max_event_log_entries
            if overflow > 0:
                del self.events[:overflow]

    def _validate_task_spec(self, task: TaskSpec) -> None:
        if not isinstance(task.task_id, str) or not task.task_id.strip():
            raise ValueError("task_id must be a non-empty string.")
        if not isinstance(task.priority, int) or task.priority < 1:
            raise ValueError("priority must be an integer >= 1.")
        if not isinstance(task.command, list):
            raise ValueError("command must be a list of strings.")
        if any((not isinstance(x, str) or not x.strip()) for x in task.command):
            raise ValueError("command entries must be non-empty strings.")
        if float(task.estimated_mem_mb) < 0:
            raise ValueError("estimated_mem_mb must be >= 0.")
        if float(task.estimated_cpu_percent) < 0:
            raise ValueError("estimated_cpu_percent must be >= 0.")
        if float(task.estimated_gpu_mem_mb) < 0:
            raise ValueError("estimated_gpu_mem_mb must be >= 0.")
        if float(task.max_runtime_sec) <= 0:
            raise ValueError("max_runtime_sec must be > 0.")
        if int(task.dry_run_ticks) < 1:
            raise ValueError("dry_run_ticks must be >= 1.")


def load_scheduler_config(path: str) -> SchedulerConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    cfg = SchedulerConfig()
    unknown_keys = [k for k in raw.keys() if not hasattr(cfg, k)]
    if unknown_keys:
        unknown_keys.sort()
        raise ValueError(f"Unknown scheduler config keys: {unknown_keys}")
    for key, value in raw.items():
        setattr(cfg, key, value)
    _validate_config(cfg)
    return cfg


def _validate_config(cfg: SchedulerConfig) -> None:
    if cfg.min_workers < 1 or cfg.max_workers < cfg.min_workers:
        raise ValueError("Invalid worker range.")
    if cfg.check_interval_sec <= 0:
        raise ValueError("check_interval_sec must be > 0.")
    if cfg.max_start_per_tick_normal < 1 or cfg.max_start_per_tick_high < 1:
        raise ValueError("max_start_per_tick_* must be >= 1.")
    if cfg.preempt_count_per_tick < 1:
        raise ValueError("preempt_count_per_tick must be >= 1.")
    if cfg.high_mode_priority_cutoff < 1:
        raise ValueError("high_mode_priority_cutoff must be >= 1.")
    if cfg.reserve_memory_mb < 0:
        raise ValueError("reserve_memory_mb must be >= 0.")
    if cfg.kill_timeout_sec <= 0:
        raise ValueError("kill_timeout_sec must be > 0.")
    if cfg.max_event_log_entries < 1:
        raise ValueError("max_event_log_entries must be >= 1.")
    if cfg.emergency_cooldown_ticks < 0:
        raise ValueError("emergency_cooldown_ticks must be >= 0.")
    if not (0.0 <= float(cfg.ema_alpha) <= 1.0):
        raise ValueError("ema_alpha must be in [0, 1].")
    if cfg.mode_hysteresis_pct < 0:
        raise ValueError("mode_hysteresis_pct must be >= 0.")
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
