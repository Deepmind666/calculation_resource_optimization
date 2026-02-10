from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resource_scheduler import (  # noqa: E402
    DynamicTaskScheduler,
    load_scheduler_config,
    ResourceMonitor,
    ResourceSnapshot,
    SchedulerConfig,
    TaskSpec,
    TaskRuntime,
)


class FakeMonitor:
    def __init__(self, snapshots: list[ResourceSnapshot]) -> None:
        self.snapshots = snapshots
        self.i = 0

    def sample(self) -> ResourceSnapshot:
        if self.i >= len(self.snapshots):
            return self.snapshots[-1]
        s = self.snapshots[self.i]
        self.i += 1
        return s


def snap(mem_pct: float, cpu_pct: float, swap_pct: float = 10.0) -> ResourceSnapshot:
    total = 8192.0
    used = total * mem_pct / 100.0
    avail = max(1.0, total - used)
    return ResourceSnapshot(
        timestamp=0.0,
        cpu_percent=cpu_pct,
        memory_percent=mem_pct,
        memory_used_mb=used,
        memory_total_mb=total,
        memory_available_mb=avail,
        swap_percent=swap_pct,
        gpu_util_percent=None,
        gpu_memory_percent=None,
        gpu_memory_used_mb=None,
        gpu_memory_total_mb=None,
    )


def snap_gpu(
    mem_pct: float,
    cpu_pct: float,
    gpu_used_mb: float,
    gpu_total_mb: float,
    gpu_util_pct: float = 40.0,
    swap_pct: float = 10.0,
) -> ResourceSnapshot:
    total = 8192.0
    used = total * mem_pct / 100.0
    avail = max(1.0, total - used)
    gpu_total = max(1.0, gpu_total_mb)
    gpu_pct = 100.0 * gpu_used_mb / gpu_total
    return ResourceSnapshot(
        timestamp=0.0,
        cpu_percent=cpu_pct,
        memory_percent=mem_pct,
        memory_used_mb=used,
        memory_total_mb=total,
        memory_available_mb=avail,
        swap_percent=swap_pct,
        gpu_util_percent=gpu_util_pct,
        gpu_memory_percent=gpu_pct,
        gpu_memory_used_mb=gpu_used_mb,
        gpu_memory_total_mb=gpu_total,
    )


class ResourceSchedulerTests(unittest.TestCase):
    def test_mode_transition(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0)
        monitor = FakeMonitor([snap(55, 30), snap(88, 50), snap(95, 70)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        self.assertEqual(sch.tick().mode, "NORMAL")
        self.assertEqual(sch.tick().mode, "HIGH")
        self.assertEqual(sch.tick().mode, "EMERGENCY")

    def test_admission_blocked_by_projected_memory(self) -> None:
        cfg = SchedulerConfig(dry_run=True, reserve_memory_mb=512, memory_emergency_pct=92.0)
        monitor = FakeMonitor([snap(90, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                task_id="T-1",
                command=[],
                priority=2,
                estimated_mem_mb=700,  # 推高到 emergency
                estimated_cpu_percent=5,
            )
        )
        report = sch.tick()
        self.assertEqual(len(report.started), 0)
        self.assertGreaterEqual(len(report.blocked), 1)

    def test_emergency_preemption(self) -> None:
        cfg = SchedulerConfig(dry_run=True, preempt_count_per_tick=2, ema_alpha=1.0)
        monitor = FakeMonitor([snap(60, 20), snap(96, 70)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)

        sch.submit_task(TaskSpec("A", [], priority=5, estimated_mem_mb=100, estimated_cpu_percent=2, dry_run_ticks=5))
        sch.submit_task(TaskSpec("B", [], priority=6, estimated_mem_mb=100, estimated_cpu_percent=2, dry_run_ticks=5))
        first = sch.tick()
        self.assertGreaterEqual(len(first.started), 1)

        second = sch.tick()
        self.assertEqual(second.mode, "EMERGENCY")
        self.assertGreaterEqual(len(second.preempted), 1)

    def test_batch_projection_prevents_oversubscribe_same_tick(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=4,
            max_start_per_tick_normal=4,
            ema_alpha=1.0,
        )
        # total=8192, used=5734(70%), 单任务估算 1000MB 时可过；两个累计后应被阻断
        monitor = FakeMonitor([snap(70, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(TaskSpec("T1", [], priority=1, estimated_mem_mb=1000, estimated_cpu_percent=5))
        sch.submit_task(TaskSpec("T2", [], priority=1, estimated_mem_mb=1000, estimated_cpu_percent=5))
        report = sch.tick()
        self.assertEqual(len(report.started), 1)
        self.assertGreaterEqual(len(report.blocked), 1)

    def test_emergency_cooldown_holds_mode(self) -> None:
        cfg = SchedulerConfig(dry_run=True, emergency_cooldown_ticks=2, ema_alpha=1.0)
        monitor = FakeMonitor([snap(95, 40), snap(70, 20), snap(70, 20), snap(70, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        self.assertEqual(sch.tick().mode, "EMERGENCY")
        self.assertEqual(sch.tick().mode, "EMERGENCY")
        self.assertEqual(sch.tick().mode, "EMERGENCY")
        self.assertEqual(sch.tick().mode, "NORMAL")

    def test_hysteresis_memory_exit_stays_high(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            memory_high_pct=85.0,
            mode_hysteresis_pct=5.0,
            cpu_high_pct=99.0,
            gpu_memory_high_pct=99.0,
        )
        monitor = FakeMonitor([snap(86, 20), snap(81, 20), snap(79, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        self.assertEqual(sch.tick().mode, "HIGH")
        self.assertEqual(sch.tick().mode, "HIGH")
        self.assertEqual(sch.tick().mode, "NORMAL")

    def test_hysteresis_gpu_exit_stays_high(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            memory_high_pct=99.0,
            cpu_high_pct=99.0,
            gpu_memory_high_pct=85.0,
            mode_hysteresis_pct=3.0,
            enable_gpu_guard=True,
        )
        monitor = FakeMonitor(
            [
                snap_gpu(40, 20, gpu_used_mb=8800, gpu_total_mb=10000),  # 88%
                snap_gpu(40, 20, gpu_used_mb=8300, gpu_total_mb=10000),  # 83% (>82 exit)
                snap_gpu(40, 20, gpu_used_mb=8100, gpu_total_mb=10000),  # 81% (<82 exit)
            ]
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        self.assertEqual(sch.tick().mode, "HIGH")
        self.assertEqual(sch.tick().mode, "HIGH")
        self.assertEqual(sch.tick().mode, "NORMAL")

    def test_timeout_count_once(self) -> None:
        cfg = SchedulerConfig(dry_run=False, max_workers=1, ema_alpha=1.0)
        monitor = FakeMonitor([snap(50, 20), snap(50, 20), snap(50, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                task_id="TIMEOUT-1",
                command=[sys.executable, "-c", "import time; time.sleep(1.0)"],
                priority=1,
                estimated_mem_mb=10,
                estimated_cpu_percent=1,
                max_runtime_sec=0.01,
            )
        )
        r1 = sch.tick()
        self.assertEqual(len(r1.started), 1)
        time.sleep(0.05)
        sch.tick()
        self.assertEqual(sch.metrics.timeout_total, 1)
        sch.shutdown()

    def test_raw_emergency_spike_not_masked_by_ema(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=0.2, memory_emergency_pct=92.0)
        monitor = FakeMonitor([snap(50, 20), snap(99, 25)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        self.assertEqual(sch.tick().mode, "NORMAL")
        self.assertEqual(sch.tick().mode, "EMERGENCY")

    def test_duplicate_task_id_rejected(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0)
        monitor = FakeMonitor([snap(55, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(TaskSpec("DUP-1", [], priority=1, estimated_mem_mb=100, estimated_cpu_percent=5))
        with self.assertRaises(ValueError):
            sch.submit_task(TaskSpec("DUP-1", [], priority=2, estimated_mem_mb=80, estimated_cpu_percent=3))

    def test_invalid_task_spec_rejected(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0)
        monitor = FakeMonitor([snap(55, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        with self.assertRaises(ValueError):
            sch.submit_task(TaskSpec("BAD-1", [], priority=1, estimated_mem_mb=-1, estimated_cpu_percent=5))

    def test_unknown_config_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad_cfg.json"
            p.write_text(
                """{
  "max_workers": 2,
  "min_workers": 1,
  "unknown_knob": 123
}""",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_scheduler_config(str(p))

    def test_stop_failure_keeps_task_tracked(self) -> None:
        class NeverStopsProcess:
            def terminate(self) -> None:
                raise RuntimeError("terminate failed")

            def wait(self, timeout: float | None = None) -> None:
                raise RuntimeError("wait failed")

            def kill(self) -> None:
                raise RuntimeError("kill failed")

            def poll(self) -> None:
                return None

        cfg = SchedulerConfig(dry_run=False, ema_alpha=1.0)
        monitor = FakeMonitor([snap(50, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)

        spec = TaskSpec(
            task_id="STUCK-1",
            command=[],
            priority=1,
            estimated_mem_mb=10,
            estimated_cpu_percent=1,
            max_runtime_sec=1.0,
        )
        sch.running[spec.task_id] = TaskRuntime(
            spec=spec,
            start_ts=time.time(),
            state="RUNNING",
            process=NeverStopsProcess(),  # type: ignore[arg-type]
        )

        ok = sch._stop_task(spec.task_id, "TIMEOUT")
        self.assertFalse(ok)
        self.assertIn(spec.task_id, sch.running)
        self.assertEqual(sch.metrics.timeout_total, 0)
        self.assertTrue(any(evt["event_type"] == "TASK_STOP_FAILED" for evt in sch.events))

    def test_event_log_is_bounded(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0, max_event_log_entries=25)
        monitor = FakeMonitor([snap(55, 20)] * 30)
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)

        for i in range(12):
            sch.submit_task(
                TaskSpec(
                    task_id=f"E-{i+1:03d}",
                    command=[],
                    priority=1,
                    estimated_mem_mb=100,
                    estimated_cpu_percent=2,
                    dry_run_ticks=1,
                )
            )

        for _ in range(30):
            sch.tick()

        self.assertLessEqual(len(sch.events), 25)

    def test_dry_run_admission_no_double_count_same_tick(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=3,
            max_start_per_tick_normal=3,
            ema_alpha=1.0,
        )
        monitor = FakeMonitor([snap(60, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(TaskSpec("D1", [], priority=1, estimated_mem_mb=800, estimated_cpu_percent=5))
        sch.submit_task(TaskSpec("D2", [], priority=1, estimated_mem_mb=800, estimated_cpu_percent=5))
        report = sch.tick()
        self.assertEqual(len(report.started), 2)
        self.assertEqual(len(report.blocked), 0)

    def test_gpu_monitor_uses_worst_card_for_multi_gpu(self) -> None:
        monitor = ResourceMonitor(enable_gpu=True)
        fake_out = "20, 1000, 10000\n30, 7000, 8000\n10, 100, 12000\n"
        with patch("resource_scheduler.shutil.which", return_value="nvidia-smi"), patch(
            "resource_scheduler.subprocess.check_output",
            return_value=fake_out,
        ):
            gpu = monitor._sample_gpu()

        self.assertAlmostEqual(float(gpu["gpu_memory_percent"]), 87.5, places=3)
        self.assertAlmostEqual(float(gpu["gpu_memory_used_mb"]), 7000.0, places=3)
        self.assertAlmostEqual(float(gpu["gpu_memory_total_mb"]), 8000.0, places=3)
        self.assertAlmostEqual(float(gpu["gpu_util_percent"]), 30.0, places=3)

    def test_gpu_admission_blocks_projected_emergency(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0, enable_gpu_guard=True, gpu_memory_emergency_pct=95.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        task = TaskSpec("GPU-BLOCK", [], priority=1, estimated_mem_mb=100, estimated_cpu_percent=2, estimated_gpu_mem_mb=1200)
        s = snap_gpu(50, 20, gpu_used_mb=6400, gpu_total_mb=8000)  # 80%
        ok, reason = sch._can_admit(task, s, mode="NORMAL")
        self.assertFalse(ok)
        self.assertIn("projected gpu memory emergency", reason)

    def test_gpu_admission_and_emergency_linkage(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            enable_gpu_guard=True,
            preempt_count_per_tick=1,
            memory_high_pct=99.0,
            cpu_high_pct=99.0,
        )
        monitor = FakeMonitor(
            [
                snap_gpu(40, 20, gpu_used_mb=3000, gpu_total_mb=10000),  # normal
                snap_gpu(40, 20, gpu_used_mb=9600, gpu_total_mb=10000),  # emergency
            ]
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                "GPU-LINK-1",
                [],
                priority=5,
                estimated_mem_mb=100,
                estimated_cpu_percent=1,
                estimated_gpu_mem_mb=200,
                preemptible=True,
                dry_run_ticks=5,
            )
        )
        first = sch.tick()
        self.assertEqual(first.mode, "NORMAL")
        self.assertGreaterEqual(len(first.started), 1)
        second = sch.tick()
        self.assertEqual(second.mode, "EMERGENCY")
        self.assertIn("GPU-LINK-1", second.preempted)

    def test_preempt_sort_key_oldest_first(self) -> None:
        cfg = SchedulerConfig(dry_run=True, preempt_count_per_tick=1, preempt_sort_key="oldest_first", ema_alpha=1.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(95, 70)]))
        a = TaskSpec("A", [], priority=5, estimated_mem_mb=100, estimated_cpu_percent=2)
        b = TaskSpec("B", [], priority=5, estimated_mem_mb=100, estimated_cpu_percent=2)
        sch.running = {
            "A": TaskRuntime(spec=a, start_ts=100.0, state="RUNNING"),
            "B": TaskRuntime(spec=b, start_ts=200.0, state="RUNNING"),
        }
        preempted = sch._preempt_low_priority(snap(95, 70))
        self.assertEqual(preempted, ["A"])

    def test_preempt_sort_key_newest_first(self) -> None:
        cfg = SchedulerConfig(dry_run=True, preempt_count_per_tick=1, preempt_sort_key="newest_first", ema_alpha=1.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(95, 70)]))
        a = TaskSpec("A", [], priority=5, estimated_mem_mb=100, estimated_cpu_percent=2)
        b = TaskSpec("B", [], priority=5, estimated_mem_mb=100, estimated_cpu_percent=2)
        sch.running = {
            "A": TaskRuntime(spec=a, start_ts=100.0, state="RUNNING"),
            "B": TaskRuntime(spec=b, start_ts=200.0, state="RUNNING"),
        }
        preempted = sch._preempt_low_priority(snap(95, 70))
        self.assertEqual(preempted, ["B"])

    def test_reclaim_target_stops_after_enough_reclaimed(self) -> None:
        cfg = SchedulerConfig(dry_run=False, preempt_count_per_tick=3, preempt_sort_key="oldest_first", ema_alpha=1.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(86, 20)]))
        a = TaskSpec("A", [], priority=5, estimated_mem_mb=1000, estimated_cpu_percent=2, preemptible=True)
        b = TaskSpec("B", [], priority=5, estimated_mem_mb=500, estimated_cpu_percent=2, preemptible=True)
        c = TaskSpec("C", [], priority=5, estimated_mem_mb=400, estimated_cpu_percent=2, preemptible=True)
        sch.running = {
            "A": TaskRuntime(spec=a, start_ts=100.0, state="RUNNING"),
            "B": TaskRuntime(spec=b, start_ts=110.0, state="RUNNING"),
            "C": TaskRuntime(spec=c, start_ts=120.0, state="RUNNING"),
        }
        snapshot = ResourceSnapshot(
            timestamp=0.0,
            cpu_percent=20.0,
            memory_percent=86.0,
            memory_used_mb=7041.2,  # reclaim_needed ~= 600MB with default high/reserve
            memory_total_mb=8192.0,
            memory_available_mb=1150.8,
            swap_percent=10.0,
            gpu_util_percent=None,
            gpu_memory_percent=None,
            gpu_memory_used_mb=None,
            gpu_memory_total_mb=None,
        )
        preempted = sch._preempt_low_priority(snapshot)
        self.assertEqual(preempted, ["A"])
        self.assertEqual(sch.metrics.preempted_total, 1)
        self.assertNotIn("A", sch.running)
        self.assertIn("B", sch.running)
        self.assertIn("C", sch.running)

    def test_non_dry_run_can_admit_skips_running_estimate(self) -> None:
        cfg = SchedulerConfig(dry_run=False, ema_alpha=1.0)
        monitor = FakeMonitor([snap(50, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        task = TaskSpec("REAL-1", ["echo", "ok"], priority=1, estimated_mem_mb=10, estimated_cpu_percent=1)
        s = snap(50, 20)
        with patch.object(
            DynamicTaskScheduler,
            "_running_estimated_load",
            side_effect=AssertionError("should not be called in non-dry_run path"),
        ):
            ok, reason = sch._can_admit(task, s, mode="NORMAL")
        self.assertTrue(ok, reason)

    def test_stuck_task_removed_after_timeout(self) -> None:
        class NeverStopsProcess:
            def terminate(self) -> None:
                raise RuntimeError("terminate failed")

            def wait(self, timeout: float | None = None) -> None:
                raise RuntimeError("wait failed")

            def kill(self) -> None:
                raise RuntimeError("kill failed")

            def poll(self) -> None:
                return None

        cfg = SchedulerConfig(
            dry_run=False,
            ema_alpha=1.0,
            kill_timeout_sec=0.01,
            stuck_task_timeout_sec=0.02,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        spec = TaskSpec(
            task_id="STUCK-TIMEOUT",
            command=[],
            priority=1,
            estimated_mem_mb=10,
            estimated_cpu_percent=1,
            max_runtime_sec=0.01,
        )
        sch.running[spec.task_id] = TaskRuntime(
            spec=spec,
            start_ts=time.time(),
            state="RUNNING",
            process=NeverStopsProcess(),  # type: ignore[arg-type]
        )

        self.assertFalse(sch._stop_task(spec.task_id, "TIMEOUT"))
        self.assertIn(spec.task_id, sch.running)
        time.sleep(0.03)
        self.assertFalse(sch._stop_task(spec.task_id, "TIMEOUT"))
        self.assertNotIn(spec.task_id, sch.running)
        self.assertEqual(sch.metrics.stuck_removed_total, 1)
        self.assertTrue(any(evt["event_type"] == "TASK_STUCK_REMOVED" for evt in sch.events))

    def test_validate_scheduler_config_respects_cli_path(self) -> None:
        root = Path(__file__).resolve().parents[2]
        script = root / "qa" / "validate_scheduler_config.py"
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "custom_bad.json"
            bad.write_text(
                json.dumps(
                    {
                        "max_workers": 2,
                        "min_workers": 1,
                        "check_interval_sec": 0.5,
                        "memory_high_pct": 85.0,
                        "memory_emergency_pct": 92.0,
                        "cpu_high_pct": 80.0,
                        "cpu_hard_pct": 95.0,
                        "swap_emergency_pct": 80.0,
                        "enable_gpu_guard": True,
                        "gpu_memory_high_pct": 85.0,
                        "gpu_memory_emergency_pct": 95.0,
                        "reserve_memory_mb": 512,
                        "high_mode_priority_cutoff": 3,
                        "preempt_count_per_tick": 1,
                        "preempt_sort_key": "oldest_first",
                        "kill_timeout_sec": 3.0,
                        "stuck_task_timeout_sec": 30.0,
                        "mode_hysteresis_pct": 3.0,
                        "emergency_cooldown_ticks": 2,
                        "ema_alpha": 0.6,
                        "max_start_per_tick_normal": 4,
                        "max_start_per_tick_high": 1,
                        "max_event_log_entries": 5000,
                        "dry_run": True,
                        "unknown_knob": 123,
                    }
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(script), str(bad)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Unknown keys", proc.stdout + proc.stderr)

    def test_real_run_projection_blocks_second_start_same_tick(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            ema_alpha=1.0,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=2,
            max_start_per_tick_normal=2,
        )
        monitor = FakeMonitor([snap(70, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        cmd = [sys.executable, "-c", "import time; time.sleep(0.4)"]
        sch.submit_task(TaskSpec("REAL-PROJ-1", cmd, priority=1, estimated_mem_mb=1000, estimated_cpu_percent=5))
        sch.submit_task(TaskSpec("REAL-PROJ-2", cmd, priority=1, estimated_mem_mb=1000, estimated_cpu_percent=5))
        report = sch.tick()
        self.assertEqual(len(report.started), 1)
        self.assertGreaterEqual(len(report.blocked), 1)
        sch.shutdown()


if __name__ == "__main__":
    unittest.main()
