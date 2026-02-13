from __future__ import annotations

from pathlib import Path
import json
import random
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
    ResourceProfile,
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
    gpu_cards: list[dict[str, float]] | None = None,
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
        gpu_cards=gpu_cards,
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

    def test_ema_alpha_full_tick_path_gpu_affinity_then_emergency_preempt(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=0.6,
            enable_gpu_guard=True,
            memory_high_pct=99.0,
            memory_emergency_pct=99.0,
            cpu_high_pct=99.0,
            gpu_memory_high_pct=85.0,
            gpu_memory_emergency_pct=95.0,
            preempt_count_per_tick=1,
            max_workers=2,
            max_start_per_tick_normal=2,
        )
        cards_normal = [
            {"index": 0.0, "memory_percent": 40.0, "util_percent": 20.0, "used_mb": 4000.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 30.0, "util_percent": 15.0, "used_mb": 3000.0, "total_mb": 10000.0},
        ]
        cards_spike = [
            {"index": 0.0, "memory_percent": 96.0, "util_percent": 40.0, "used_mb": 9600.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 35.0, "util_percent": 18.0, "used_mb": 3500.0, "total_mb": 10000.0},
        ]
        monitor = FakeMonitor(
            [
                snap_gpu(60, 20, gpu_used_mb=4000.0, gpu_total_mb=10000.0, gpu_cards=cards_normal),
                snap_gpu(60, 20, gpu_used_mb=4000.0, gpu_total_mb=10000.0, gpu_cards=cards_normal),
                snap_gpu(60, 20, gpu_used_mb=9600.0, gpu_total_mb=10000.0, gpu_cards=cards_spike),
            ]
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)

        # Tick-1 seeds EMA state.
        self.assertEqual(sch.tick().mode, "NORMAL")
        sch.submit_task(
            TaskSpec(
                "EMA-FULL-GPU-1",
                [],
                priority=5,
                estimated_mem_mb=100,
                estimated_cpu_percent=2,
                estimated_gpu_mem_mb=600,
                target_gpu_index=0,
                preemptible=True,
                dry_run_ticks=5,
            )
        )
        second = sch.tick()
        self.assertEqual(second.mode, "NORMAL")
        self.assertEqual(second.started, ["EMA-FULL-GPU-1"])
        third = sch.tick()
        self.assertEqual(third.mode, "EMERGENCY")
        self.assertIn("EMA-FULL-GPU-1", third.preempted)

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
        with self.assertRaises(ValueError):
            sch.submit_task(
                TaskSpec(
                    "BAD-2",
                    [],
                    priority=1,
                    estimated_mem_mb=10,
                    estimated_cpu_percent=1,
                    estimated_gpu_mem_mb=1,
                    target_gpu_index=-1,
                )
            )

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

    def test_blocked_metrics_split_event_and_unique_task_count(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=1,
            max_start_per_tick_normal=1,
        )
        monitor = FakeMonitor([snap(90, 20), snap(90, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(TaskSpec("BLOCK-ONCE", [], priority=1, estimated_mem_mb=700, estimated_cpu_percent=2))

        # Same task is blocked on two ticks.
        sch.tick()
        sch.tick()
        self.assertEqual(sch.metrics.blocked_total, 2)
        self.assertEqual(sch.metrics.blocked_task_total, 1)

    def test_blocked_metrics_unique_count_with_multiple_tasks(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=2,
            max_start_per_tick_normal=2,
        )
        monitor = FakeMonitor([snap(90, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(TaskSpec("BLOCK-A", [], priority=1, estimated_mem_mb=700, estimated_cpu_percent=2))
        sch.submit_task(TaskSpec("BLOCK-B", [], priority=1, estimated_mem_mb=700, estimated_cpu_percent=2))

        sch.tick()
        self.assertEqual(sch.metrics.blocked_total, 2)
        self.assertEqual(sch.metrics.blocked_task_total, 2)

    def test_blocked_task_tracking_released_after_completion(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=1,
            max_start_per_tick_normal=1,
        )
        monitor = FakeMonitor([snap(90, 20), snap(50, 20), snap(50, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                "BLOCK-THEN-RUN",
                [],
                priority=1,
                estimated_mem_mb=700,
                estimated_cpu_percent=2,
                dry_run_ticks=1,
            )
        )
        # Tick 1: blocked.
        sch.tick()
        self.assertIn("BLOCK-THEN-RUN", sch._blocked_task_ids)
        # Tick 2: admitted.
        sch.tick()
        self.assertIn("BLOCK-THEN-RUN", sch.running)
        # Tick 3: finishes and tracking is released.
        sch.tick()
        self.assertNotIn("BLOCK-THEN-RUN", sch._blocked_task_ids)

    def test_emergency_pending_tasks_emit_per_task_block_events(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0)
        monitor = FakeMonitor([snap(95, 40)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(TaskSpec("E-P1", [], priority=1, estimated_mem_mb=100, estimated_cpu_percent=1))
        sch.submit_task(TaskSpec("E-P2", [], priority=2, estimated_mem_mb=100, estimated_cpu_percent=1))

        report = sch.tick()
        self.assertEqual(report.mode, "EMERGENCY")
        blocked_ids = {item["task_id"] for item in report.blocked}
        self.assertEqual(blocked_ids, {"E-P1", "E-P2"})
        self.assertEqual(sch.metrics.blocked_total, 2)
        self.assertEqual(sch.metrics.blocked_task_total, 2)
        blocked_events = [evt for evt in sch.events if evt["event_type"] == "TASK_BLOCKED"]
        self.assertEqual(len(blocked_events), 2)
        self.assertTrue(all(evt["payload"]["source"] == "pending" for evt in blocked_events))

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
        self.assertEqual(len(gpu["gpu_cards"]), 3)
        self.assertAlmostEqual(float(gpu["gpu_cards"][0]["memory_percent"]), 10.0, places=3)

    def test_gpu_monitor_skips_malformed_rows(self) -> None:
        monitor = ResourceMonitor(enable_gpu=True)
        fake_out = "20, 1000, 10000\nN/A, N/A, N/A\n30, 7000, 8000\n"
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

    def test_gpu_affinity_uses_target_card_projection(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0, enable_gpu_guard=True, gpu_memory_emergency_pct=95.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        cards = [
            {"index": 0.0, "memory_percent": 10.0, "util_percent": 20.0, "used_mb": 1000.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 90.0, "util_percent": 40.0, "used_mb": 9000.0, "total_mb": 10000.0},
        ]
        s = snap_gpu(
            50,
            20,
            gpu_used_mb=9000,
            gpu_total_mb=10000,
            gpu_util_pct=40.0,
            gpu_cards=cards,
        )
        no_affinity = TaskSpec(
            "GPU-NO-AFF",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1000,
        )
        with_affinity = TaskSpec(
            "GPU-AFF-0",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1000,
            target_gpu_index=0,
        )

        ok_no_aff, reason_no_aff = sch._can_admit(no_affinity, s, mode="NORMAL")
        ok_aff, reason_aff = sch._can_admit(with_affinity, s, mode="NORMAL")
        self.assertFalse(ok_no_aff)
        self.assertIn("projected gpu memory emergency", reason_no_aff)
        self.assertTrue(ok_aff, reason_aff)

    def test_gpu_affinity_survives_ema_smoothing_snapshot_path(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=0.6,
            enable_gpu_guard=True,
            gpu_memory_high_pct=99.0,
            memory_high_pct=99.0,
            cpu_high_pct=99.0,
            gpu_memory_emergency_pct=95.0,
            max_workers=1,
            max_start_per_tick_normal=1,
        )
        cards = [
            {"index": 0.0, "memory_percent": 10.0, "util_percent": 20.0, "used_mb": 1000.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 90.0, "util_percent": 40.0, "used_mb": 9000.0, "total_mb": 10000.0},
        ]
        monitor = FakeMonitor(
            [
                snap_gpu(50, 20, gpu_used_mb=9000, gpu_total_mb=10000, gpu_util_pct=40.0, gpu_cards=cards),
                snap_gpu(50, 20, gpu_used_mb=9000, gpu_total_mb=10000, gpu_util_pct=40.0, gpu_cards=cards),
            ]
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        # Seed EMA state so second tick goes through smoothing construction branch.
        sch.tick()
        sch.submit_task(
            TaskSpec(
                "GPU-AFF-EMA",
                [],
                priority=1,
                estimated_mem_mb=100,
                estimated_cpu_percent=2,
                estimated_gpu_mem_mb=1000,
                target_gpu_index=0,
            )
        )
        second = sch.tick()
        self.assertEqual(len(second.started), 1)
        self.assertEqual(len(second.blocked), 0)

    def test_gpu_affinity_rejects_unavailable_target(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0, enable_gpu_guard=True, gpu_memory_emergency_pct=95.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        cards = [
            {"index": 0.0, "memory_percent": 10.0, "util_percent": 20.0, "used_mb": 1000.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 20.0, "util_percent": 30.0, "used_mb": 2000.0, "total_mb": 10000.0},
        ]
        s = snap_gpu(
            50,
            20,
            gpu_used_mb=2000,
            gpu_total_mb=10000,
            gpu_util_pct=30.0,
            gpu_cards=cards,
        )
        task = TaskSpec(
            "GPU-AFF-BAD",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1000,
            target_gpu_index=3,
        )
        ok, reason = sch._can_admit(task, s, mode="NORMAL")
        self.assertFalse(ok)
        self.assertIn("target gpu unavailable", reason)

    def test_real_run_gpu_projection_uses_per_gpu_planned_budget(self) -> None:
        cfg = SchedulerConfig(dry_run=False, ema_alpha=1.0, enable_gpu_guard=True, gpu_memory_emergency_pct=95.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        cards = [
            {"index": 0.0, "memory_percent": 85.0, "util_percent": 30.0, "used_mb": 8500.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 10.0, "util_percent": 20.0, "used_mb": 1000.0, "total_mb": 10000.0},
        ]
        s = snap_gpu(
            50,
            20,
            gpu_used_mb=8500,
            gpu_total_mb=10000,
            gpu_util_pct=30.0,
            gpu_cards=cards,
        )
        task = TaskSpec(
            "GPU-REAL-AFF-0",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=800,
            target_gpu_index=0,
        )

        # Planned GPU load exists on card-1 only; it must not pollute card-0 projection.
        ok, reason = sch._can_admit(
            task,
            s,
            mode="NORMAL",
            planned_extra_gpu_by_index={1: 500.0},
            planned_extra_gpu_unbound_mb=0.0,
        )
        self.assertTrue(ok, reason)

    def test_dry_run_gpu_projection_uses_per_gpu_running_budget(self) -> None:
        cfg = SchedulerConfig(dry_run=True, ema_alpha=1.0, enable_gpu_guard=True, gpu_memory_emergency_pct=95.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        cards = [
            {"index": 0.0, "memory_percent": 85.0, "util_percent": 30.0, "used_mb": 8500.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 10.0, "util_percent": 20.0, "used_mb": 1000.0, "total_mb": 10000.0},
        ]
        running_spec = TaskSpec(
            "RUN-GPU1",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1000,
            target_gpu_index=1,
            dry_run_ticks=5,
        )
        sch.running[running_spec.task_id] = TaskRuntime(
            spec=running_spec,
            start_ts=time.time(),
            state="RUNNING",
            process=None,
            remaining_ticks=3,
        )
        s = snap_gpu(
            50,
            20,
            gpu_used_mb=8500,
            gpu_total_mb=10000,
            gpu_util_pct=30.0,
            gpu_cards=cards,
        )
        task = TaskSpec(
            "GPU-DRY-AFF-0",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=800,
            target_gpu_index=0,
        )
        ok, reason = sch._can_admit(task, s, mode="NORMAL")
        self.assertTrue(ok, reason)

    def test_real_run_unbound_gpu_projection_remains_conservative(self) -> None:
        cfg = SchedulerConfig(dry_run=False, ema_alpha=1.0, enable_gpu_guard=True, gpu_memory_emergency_pct=95.0)
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        cards = [
            {"index": 0.0, "memory_percent": 85.0, "util_percent": 30.0, "used_mb": 8500.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 10.0, "util_percent": 20.0, "used_mb": 1000.0, "total_mb": 10000.0},
        ]
        s = snap_gpu(
            50,
            20,
            gpu_used_mb=8500,
            gpu_total_mb=10000,
            gpu_util_pct=30.0,
            gpu_cards=cards,
        )
        task = TaskSpec(
            "GPU-REAL-UNBOUND",
            [],
            priority=1,
            estimated_mem_mb=100,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=800,
        )

        ok, reason = sch._can_admit(
            task,
            s,
            mode="NORMAL",
            planned_extra_gpu_by_index={1: 500.0},
            planned_extra_gpu_unbound_mb=0.0,
        )
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

    def test_dry_run_running_estimate_computed_once_per_tick(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            max_workers=3,
            max_start_per_tick_normal=3,
            reserve_memory_mb=256,
            memory_emergency_pct=99.0,
            enable_gpu_guard=True,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(40, 20)]))
        sch.submit_task(TaskSpec("CACHE-1", [], priority=1, estimated_mem_mb=100, estimated_cpu_percent=2))
        sch.submit_task(TaskSpec("CACHE-2", [], priority=1, estimated_mem_mb=100, estimated_cpu_percent=2))
        sch.submit_task(TaskSpec("CACHE-3", [], priority=1, estimated_mem_mb=100, estimated_cpu_percent=2))

        with patch.object(sch, "_running_estimated_load", wraps=sch._running_estimated_load) as load_mock, patch.object(
            sch,
            "_running_estimated_gpu_breakdown",
            wraps=sch._running_estimated_gpu_breakdown,
        ) as gpu_mock:
            report = sch.tick()

        self.assertEqual(len(report.started), 3)
        self.assertEqual(load_mock.call_count, 1)
        self.assertEqual(gpu_mock.call_count, 1)

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
        self.assertEqual(sch.metrics.timeout_total, 1)
        self.assertTrue(any(evt["event_type"] == "TASK_STUCK_REMOVED" for evt in sch.events))

    def test_stuck_removed_counts_toward_preempt_reclaim_target(self) -> None:
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
            preempt_count_per_tick=2,
            preempt_sort_key="oldest_first",
            kill_timeout_sec=0.01,
            stuck_task_timeout_sec=0.01,
            ema_alpha=1.0,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(86, 20)]))
        a = TaskSpec("STUCK-A", [], priority=5, estimated_mem_mb=1000, estimated_cpu_percent=2, preemptible=True)
        b = TaskSpec("RUN-B", [], priority=5, estimated_mem_mb=500, estimated_cpu_percent=2, preemptible=True)
        sch.running = {
            "STUCK-A": TaskRuntime(
                spec=a,
                start_ts=100.0,
                state="RUNNING",
                process=NeverStopsProcess(),  # type: ignore[arg-type]
                stop_requested_ts=(time.time() - 1.0),
                stop_reason="PREEMPTED",
            ),
            "RUN-B": TaskRuntime(spec=b, start_ts=110.0, state="RUNNING"),
        }
        snapshot = ResourceSnapshot(
            timestamp=0.0,
            cpu_percent=20.0,
            memory_percent=86.0,
            memory_used_mb=7041.2,  # reclaim_needed ~= 590MB with default high/reserve
            memory_total_mb=8192.0,
            memory_available_mb=1150.8,
            swap_percent=10.0,
            gpu_util_percent=None,
            gpu_memory_percent=None,
            gpu_memory_used_mb=None,
            gpu_memory_total_mb=None,
        )

        preempted = sch._preempt_low_priority(snapshot)
        self.assertEqual(preempted, ["STUCK-A"])
        self.assertNotIn("STUCK-A", sch.running)
        self.assertIn("RUN-B", sch.running)
        self.assertEqual(sch.metrics.stuck_removed_total, 1)
        self.assertEqual(sch.metrics.preempted_total, 1)
        self.assertTrue(
            any(
                evt["event_type"] == "TASK_STUCK_REMOVED"
                and evt["payload"].get("reason") == "PREEMPTED"
                for evt in sch.events
            )
        )

    def test_gpu_emergency_preempts_gpu_heavy_task_first(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            preempt_count_per_tick=2,
            preempt_sort_key="oldest_first",
            ema_alpha=1.0,
            enable_gpu_guard=True,
            gpu_memory_high_pct=85.0,
            gpu_memory_emergency_pct=95.0,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(60, 20)]))
        gpu_heavy = TaskSpec(
            "GPU-HEAVY",
            [],
            priority=5,
            estimated_mem_mb=200,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1200,
            target_gpu_index=0,
            preemptible=True,
        )
        mem_heavy = TaskSpec(
            "MEM-HEAVY",
            [],
            priority=5,
            estimated_mem_mb=5000,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=0,
            target_gpu_index=0,
            preemptible=True,
        )
        sch.running = {
            "GPU-HEAVY": TaskRuntime(spec=gpu_heavy, start_ts=100.0, state="RUNNING"),
            "MEM-HEAVY": TaskRuntime(spec=mem_heavy, start_ts=110.0, state="RUNNING"),
        }
        cards = [
            {"index": 0.0, "memory_percent": 96.0, "util_percent": 40.0, "used_mb": 9600.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 20.0, "util_percent": 20.0, "used_mb": 2000.0, "total_mb": 10000.0},
        ]
        snapshot = snap_gpu(
            60,
            20,
            gpu_used_mb=9600.0,
            gpu_total_mb=10000.0,
            gpu_util_pct=40.0,
            gpu_cards=cards,
        )

        preempted = sch._preempt_low_priority(snapshot)
        self.assertEqual(preempted, ["GPU-HEAVY"])
        self.assertNotIn("GPU-HEAVY", sch.running)
        self.assertIn("MEM-HEAVY", sch.running)

    def test_preempt_uses_raw_view_for_emergency_dimension_detection(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            preempt_count_per_tick=1,
            preempt_sort_key="oldest_first",
            ema_alpha=0.6,
            enable_gpu_guard=True,
            gpu_memory_high_pct=85.0,
            gpu_memory_emergency_pct=95.0,
            memory_high_pct=99.0,
            memory_emergency_pct=99.0,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(60, 20)]))
        gpu_hot = TaskSpec(
            "GPU-HOT",
            [],
            priority=5,
            estimated_mem_mb=200,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1200,
            target_gpu_index=0,
            preemptible=True,
        )
        mem_heavy = TaskSpec(
            "MEM-HEAVY",
            [],
            priority=5,
            estimated_mem_mb=5000,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=0,
            preemptible=True,
        )
        sch.running = {
            "GPU-HOT": TaskRuntime(spec=gpu_hot, start_ts=100.0, state="RUNNING"),
            "MEM-HEAVY": TaskRuntime(spec=mem_heavy, start_ts=110.0, state="RUNNING"),
        }
        smoothed_cards = [
            {"index": 0.0, "memory_percent": 85.0, "util_percent": 30.0, "used_mb": 8500.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 20.0, "util_percent": 20.0, "used_mb": 2000.0, "total_mb": 10000.0},
        ]
        raw_cards = [
            {"index": 0.0, "memory_percent": 96.0, "util_percent": 40.0, "used_mb": 9600.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 20.0, "util_percent": 20.0, "used_mb": 2000.0, "total_mb": 10000.0},
        ]
        smoothed = snap_gpu(
            60,
            20,
            gpu_used_mb=8500.0,
            gpu_total_mb=10000.0,
            gpu_util_pct=30.0,
            gpu_cards=smoothed_cards,
        )
        raw = snap_gpu(
            60,
            20,
            gpu_used_mb=9600.0,
            gpu_total_mb=10000.0,
            gpu_util_pct=40.0,
            gpu_cards=raw_cards,
        )

        preempted = sch._preempt_low_priority(smoothed, raw)
        self.assertEqual(preempted, ["GPU-HOT"])
        self.assertNotIn("GPU-HOT", sch.running)
        self.assertIn("MEM-HEAVY", sch.running)

    def test_mixed_emergency_preempt_score_uses_normalized_resources(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            preempt_count_per_tick=1,
            preempt_sort_key="oldest_first",
            ema_alpha=1.0,
            enable_gpu_guard=True,
            memory_high_pct=85.0,
            memory_emergency_pct=92.0,
            gpu_memory_high_pct=85.0,
            gpu_memory_emergency_pct=95.0,
            reserve_memory_mb=512,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(60, 20)]))
        mem_heavy = TaskSpec(
            "MEM-HEAVY",
            [],
            priority=5,
            estimated_mem_mb=2000,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=0,
            preemptible=True,
        )
        mixed_balanced = TaskSpec(
            "MIXED-BALANCED",
            [],
            priority=5,
            estimated_mem_mb=700,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=1200,
            target_gpu_index=0,
            preemptible=True,
        )
        sch.running = {
            "MEM-HEAVY": TaskRuntime(spec=mem_heavy, start_ts=100.0, state="RUNNING"),
            "MIXED-BALANCED": TaskRuntime(spec=mixed_balanced, start_ts=110.0, state="RUNNING"),
        }
        cards = [
            {"index": 0.0, "memory_percent": 96.0, "util_percent": 40.0, "used_mb": 9600.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 20.0, "util_percent": 20.0, "used_mb": 2000.0, "total_mb": 10000.0},
        ]
        snapshot = ResourceSnapshot(
            timestamp=0.0,
            cpu_percent=20.0,
            memory_percent=93.0,
            memory_used_mb=30474.24,
            memory_total_mb=32768.0,
            memory_available_mb=2293.76,
            swap_percent=10.0,
            gpu_util_percent=40.0,
            gpu_memory_percent=96.0,
            gpu_memory_used_mb=9600.0,
            gpu_memory_total_mb=10000.0,
            gpu_cards=cards,
        )

        preempted = sch._preempt_low_priority(snapshot)
        self.assertEqual(preempted, ["MIXED-BALANCED"])
        self.assertNotIn("MIXED-BALANCED", sch.running)
        self.assertIn("MEM-HEAVY", sch.running)

    def test_mixed_emergency_prefers_dual_reclaim_contributor(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            preempt_count_per_tick=1,
            preempt_sort_key="oldest_first",
            ema_alpha=1.0,
            enable_gpu_guard=True,
            memory_high_pct=80.0,
            memory_emergency_pct=85.0,
            gpu_memory_high_pct=85.0,
            gpu_memory_emergency_pct=95.0,
            reserve_memory_mb=512,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(60, 20)]))
        mem_heavy = TaskSpec(
            "MEM-HEAVY-ONE-SIDED",
            [],
            priority=5,
            estimated_mem_mb=1400,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=0,
            preemptible=True,
        )
        dual_balanced = TaskSpec(
            "DUAL-BALANCED",
            [],
            priority=5,
            estimated_mem_mb=600,
            estimated_cpu_percent=2,
            estimated_gpu_mem_mb=700,
            target_gpu_index=0,
            preemptible=True,
        )
        sch.running = {
            "MEM-HEAVY-ONE-SIDED": TaskRuntime(spec=mem_heavy, start_ts=100.0, state="RUNNING"),
            "DUAL-BALANCED": TaskRuntime(spec=dual_balanced, start_ts=110.0, state="RUNNING"),
        }
        cards = [
            {"index": 0.0, "memory_percent": 97.0, "util_percent": 45.0, "used_mb": 9700.0, "total_mb": 10000.0},
            {"index": 1.0, "memory_percent": 20.0, "util_percent": 20.0, "used_mb": 2000.0, "total_mb": 10000.0},
        ]
        snapshot = ResourceSnapshot(
            timestamp=0.0,
            cpu_percent=20.0,
            memory_percent=85.0,
            memory_used_mb=8500.0,
            memory_total_mb=10000.0,
            memory_available_mb=1500.0,
            swap_percent=10.0,
            gpu_util_percent=45.0,
            gpu_memory_percent=97.0,
            gpu_memory_used_mb=9700.0,
            gpu_memory_total_mb=10000.0,
            gpu_cards=cards,
        )

        preempted = sch._preempt_low_priority(snapshot)
        self.assertEqual(preempted, ["DUAL-BALANCED"])
        self.assertNotIn("DUAL-BALANCED", sch.running)
        self.assertIn("MEM-HEAVY-ONE-SIDED", sch.running)

    def test_real_process_completes_and_is_accounted(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            ema_alpha=1.0,
            max_workers=1,
            max_start_per_tick_normal=1,
            check_interval_sec=0.01,
        )
        monitor = FakeMonitor([snap(50, 20)] * 20)
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                task_id="REAL-COMPLETE-1",
                command=[sys.executable, "-c", "import time; time.sleep(0.05)"],
                priority=1,
                estimated_mem_mb=50,
                estimated_cpu_percent=2,
                max_runtime_sec=2.0,
            )
        )
        first = sch.tick()
        self.assertEqual(first.started, ["REAL-COMPLETE-1"])

        deadline = time.time() + 1.5
        while time.time() < deadline and "REAL-COMPLETE-1" in sch.running:
            time.sleep(0.01)
            sch.tick()
        self.assertNotIn("REAL-COMPLETE-1", sch.running)
        self.assertEqual(sch.metrics.completed_total, 1)
        self.assertTrue(
            any(
                evt["event_type"] == "TASK_FINISHED"
                and evt["payload"].get("task_id") == "REAL-COMPLETE-1"
                and evt["payload"].get("state") == "COMPLETED"
                for evt in sch.events
            )
        )
        sch.shutdown()

    def test_real_process_timeout_stops_process_object(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            ema_alpha=1.0,
            max_workers=1,
            max_start_per_tick_normal=1,
            kill_timeout_sec=0.2,
            check_interval_sec=0.01,
        )
        monitor = FakeMonitor([snap(50, 20)] * 20)
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                task_id="REAL-TIMEOUT-1",
                command=[sys.executable, "-c", "import time; time.sleep(2.0)"],
                priority=1,
                estimated_mem_mb=50,
                estimated_cpu_percent=2,
                max_runtime_sec=0.02,
            )
        )
        first = sch.tick()
        self.assertEqual(first.started, ["REAL-TIMEOUT-1"])
        runtime = sch.running["REAL-TIMEOUT-1"]
        proc = runtime.process
        self.assertIsNotNone(proc)

        deadline = time.time() + 1.5
        while time.time() < deadline and "REAL-TIMEOUT-1" in sch.running:
            time.sleep(0.01)
            sch.tick()

        self.assertNotIn("REAL-TIMEOUT-1", sch.running)
        self.assertEqual(sch.metrics.timeout_total, 1)
        self.assertIsNotNone(proc)
        assert proc is not None
        self.assertIsNotNone(proc.poll())
        sch.shutdown()

    def test_long_run_randomized_snapshots_preserve_state_invariants(self) -> None:
        rnd = random.Random(12345)
        snapshots: list[ResourceSnapshot] = []
        for i in range(220):
            base_mem = 62.0 + 18.0 * (1 if (i % 37 == 0) else 0) + rnd.uniform(-12.0, 12.0)
            mem_pct = max(20.0, min(98.0, base_mem))
            cpu_pct = max(5.0, min(99.0, 35.0 + rnd.uniform(-20.0, 35.0)))
            swap_pct = max(0.0, min(95.0, 10.0 + rnd.uniform(-8.0, 25.0)))
            snapshots.append(snap(mem_pct, cpu_pct, swap_pct))

        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=0.6,
            enable_gpu_guard=False,
            max_workers=4,
            max_start_per_tick_normal=4,
            max_start_per_tick_high=2,
            max_event_log_entries=400,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor(snapshots))

        submitted = 0
        for tick_idx in range(220):
            if tick_idx % 3 == 0 and submitted < 120:
                submitted += 1
                sch.submit_task(
                    TaskSpec(
                        task_id=f"RAND-{submitted:03d}",
                        command=[],
                        priority=rnd.randint(1, 6),
                        estimated_mem_mb=rnd.randint(40, 420),
                        estimated_cpu_percent=float(rnd.randint(1, 12)),
                        dry_run_ticks=rnd.randint(1, 5),
                    )
                )

            report = sch.tick()
            self.assertEqual(report.running_count, len(sch.running))
            self.assertEqual(report.pending_count, len(sch.pending))
            self.assertLessEqual(len(sch.running), cfg.max_workers)
            self.assertLessEqual(len(sch.events), cfg.max_event_log_entries)
            self.assertLessEqual(sch.metrics.started_total, sch.metrics.submitted_total)
            self.assertLessEqual(sch.metrics.blocked_task_total, sch.metrics.submitted_total)
            pending_ids = [task.task_id for _, _, task in sch.pending]
            self.assertEqual(len(pending_ids), len(set(pending_ids)))

        sch.shutdown()

    def test_estimation_error_overestimate_blocks_large_task_but_small_task_runs(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            reserve_memory_mb=512,
            memory_emergency_pct=92.0,
            max_workers=2,
            max_start_per_tick_normal=2,
        )
        monitor = FakeMonitor([snap(60, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                task_id="EST-OVER-LARGE",
                command=[],
                priority=1,
                estimated_mem_mb=7000,
                estimated_cpu_percent=5,
            )
        )
        sch.submit_task(
            TaskSpec(
                task_id="EST-OVER-SMALL",
                command=[],
                priority=1,
                estimated_mem_mb=120,
                estimated_cpu_percent=2,
            )
        )
        report = sch.tick()
        self.assertIn("EST-OVER-SMALL", report.started)
        blocked_ids = {b["task_id"] for b in report.blocked}
        self.assertIn("EST-OVER-LARGE", blocked_ids)

    def test_estimation_error_underestimate_then_raw_spike_preempts(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            ema_alpha=1.0,
            preempt_count_per_tick=1,
            memory_high_pct=85.0,
            memory_emergency_pct=92.0,
            cpu_high_pct=99.0,
            gpu_memory_high_pct=99.0,
            max_workers=1,
            max_start_per_tick_normal=1,
        )
        monitor = FakeMonitor([snap(50, 20), snap(97, 20)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)
        sch.submit_task(
            TaskSpec(
                task_id="EST-UNDER-1",
                command=[],
                priority=5,
                estimated_mem_mb=50,
                estimated_cpu_percent=2,
                preemptible=True,
                dry_run_ticks=5,
            )
        )
        first = sch.tick()
        self.assertEqual(first.mode, "NORMAL")
        self.assertEqual(first.started, ["EST-UNDER-1"])
        second = sch.tick()
        self.assertEqual(second.mode, "EMERGENCY")
        self.assertIn("EST-UNDER-1", second.preempted)

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
                        "enable_estimation_autocalibration": False,
                        "profile_ema_alpha": 0.5,
                        "profile_safety_multiplier": 1.25,
                        "profile_min_samples": 3,
                        "runtime_sample_interval_sec": 0.2,
                        "max_resource_profiles": 1024,
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

    def test_invalid_gpu_threshold_relation_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad_gpu_cfg.json"
            p.write_text(
                """{
  "max_workers": 2,
  "min_workers": 1,
  "check_interval_sec": 0.5,
  "memory_high_pct": 85.0,
  "memory_emergency_pct": 92.0,
  "cpu_high_pct": 80.0,
  "cpu_hard_pct": 95.0,
  "swap_emergency_pct": 80.0,
  "enable_gpu_guard": true,
  "gpu_memory_high_pct": 96.0,
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
  "dry_run": true
}""",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_scheduler_config(str(p))

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

    def test_task_profile_updates_with_ema(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            enable_estimation_autocalibration=True,
            profile_ema_alpha=0.5,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        spec = TaskSpec(
            "PROFILE-EMA-1",
            ["python", "-c", "print(1)"],
            priority=1,
            estimated_mem_mb=200,
            estimated_cpu_percent=5,
        )
        r1 = TaskRuntime(
            spec=spec,
            start_ts=0.0,
            state="COMPLETED",
            profile_key="python",
            observed_peak_mem_mb=1000.0,
            observed_peak_cpu_pct=20.0,
        )
        r2 = TaskRuntime(
            spec=spec,
            start_ts=0.0,
            state="COMPLETED",
            profile_key="python",
            observed_peak_mem_mb=1400.0,
            observed_peak_cpu_pct=40.0,
        )
        sch._update_resource_profile(r1)
        sch._update_resource_profile(r2)

        profile = sch._resource_profiles["python"]
        self.assertEqual(profile.samples, 2)
        self.assertAlmostEqual(profile.ema_peak_mem_mb, 1200.0, places=3)
        self.assertAlmostEqual(profile.ema_peak_cpu_pct, 30.0, places=3)
        self.assertGreaterEqual(
            len([evt for evt in sch.events if evt["event_type"] == "TASK_PROFILE_UPDATED"]),
            2,
        )

    def test_task_profile_updates_with_gpu_ema(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            enable_estimation_autocalibration=True,
            profile_ema_alpha=0.5,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        spec = TaskSpec(
            "PROFILE-GPU-EMA-1",
            ["python", "-c", "print(1)"],
            priority=1,
            estimated_mem_mb=200,
            estimated_cpu_percent=5,
            estimated_gpu_mem_mb=100,
        )
        r1 = TaskRuntime(
            spec=spec,
            start_ts=0.0,
            state="COMPLETED",
            profile_key="python",
            observed_peak_gpu_mem_mb=1000.0,
        )
        r2 = TaskRuntime(
            spec=spec,
            start_ts=0.0,
            state="COMPLETED",
            profile_key="python",
            observed_peak_gpu_mem_mb=1400.0,
        )
        sch._update_resource_profile(r1)
        sch._update_resource_profile(r2)

        profile = sch._resource_profiles["python"]
        self.assertEqual(profile.samples, 2)
        self.assertAlmostEqual(profile.ema_peak_gpu_mem_mb, 1200.0, places=3)
        gpu_events = [evt for evt in sch.events if evt["event_type"] == "TASK_PROFILE_UPDATED"]
        self.assertGreaterEqual(len(gpu_events), 2)
        self.assertIn("ema_peak_gpu_mem_mb", gpu_events[-1]["payload"])

    def test_gpu_pid_memory_parser_aggregates_and_skips_invalid_rows(self) -> None:
        cfg = SchedulerConfig(
            dry_run=False,
            enable_estimation_autocalibration=True,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        fake_out = "\n".join(
            [
                "123, 100",
                "123, 50 MiB",
                "456, N/A",
                "bad line",
                "789, 20",
            ]
        )
        with patch("resource_scheduler.shutil.which", return_value="nvidia-smi"), patch(
            "resource_scheduler.subprocess.check_output",
            return_value=fake_out,
        ):
            usage = sch._read_gpu_pid_memory_mb()
        self.assertAlmostEqual(float(usage[123]), 150.0, places=3)
        self.assertAlmostEqual(float(usage[789]), 20.0, places=3)
        self.assertNotIn(456, usage)

    def test_autocalibration_adjusts_task_estimates_on_submit(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            enable_estimation_autocalibration=True,
            profile_min_samples=2,
            profile_safety_multiplier=1.2,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        sch._resource_profiles["python"] = ResourceProfile(
            samples=3,
            ema_peak_mem_mb=900.0,
            ema_peak_cpu_pct=25.0,
            last_updated_ts=time.time(),
        )
        sch.submit_task(
            TaskSpec(
                "CALIBRATE-1",
                ["python", "-c", "print(1)"],
                priority=1,
                estimated_mem_mb=200,
                estimated_cpu_percent=5.0,
            )
        )
        queued = sch.pending[0][2]
        self.assertEqual(queued.profile_key, "python")
        self.assertGreaterEqual(queued.estimated_mem_mb, 1080)
        self.assertGreaterEqual(queued.estimated_cpu_percent, 30.0)
        self.assertTrue(any(evt["event_type"] == "TASK_ESTIMATE_CALIBRATED" for evt in sch.events))

    def test_autocalibration_adjusts_gpu_estimate_on_submit(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            enable_estimation_autocalibration=True,
            profile_min_samples=2,
            profile_safety_multiplier=1.2,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        sch._resource_profiles["python"] = ResourceProfile(
            samples=3,
            ema_peak_mem_mb=200.0,
            ema_peak_cpu_pct=5.0,
            ema_peak_gpu_mem_mb=900.0,
            last_updated_ts=time.time(),
        )
        sch.submit_task(
            TaskSpec(
                "CALIBRATE-GPU-1",
                ["python", "-c", "print(1)"],
                priority=1,
                estimated_mem_mb=200,
                estimated_cpu_percent=5.0,
                estimated_gpu_mem_mb=100,
            )
        )
        queued = sch.pending[0][2]
        self.assertEqual(queued.profile_key, "python")
        self.assertGreaterEqual(queued.estimated_gpu_mem_mb, 1080)
        calibrate_events = [evt for evt in sch.events if evt["event_type"] == "TASK_ESTIMATE_CALIBRATED"]
        self.assertTrue(calibrate_events)
        self.assertIn("estimated_gpu_mem_mb_before", calibrate_events[-1]["payload"])
        self.assertIn("estimated_gpu_mem_mb_after", calibrate_events[-1]["payload"])

    def test_autocalibration_disabled_keeps_estimates_unchanged(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            enable_estimation_autocalibration=False,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))
        sch._resource_profiles["python"] = ResourceProfile(
            samples=5,
            ema_peak_mem_mb=2000.0,
            ema_peak_cpu_pct=90.0,
            last_updated_ts=time.time(),
        )
        sch.submit_task(
            TaskSpec(
                "CALIBRATE-DISABLED-1",
                ["python", "-c", "print(1)"],
                priority=1,
                estimated_mem_mb=300,
                estimated_cpu_percent=10.0,
            )
        )
        queued = sch.pending[0][2]
        self.assertEqual(queued.estimated_mem_mb, 300)
        self.assertEqual(queued.estimated_cpu_percent, 10.0)
        self.assertFalse(any(evt["event_type"] == "TASK_ESTIMATE_CALIBRATED" for evt in sch.events))

    def test_resource_profile_pool_is_bounded(self) -> None:
        cfg = SchedulerConfig(
            dry_run=True,
            enable_estimation_autocalibration=True,
            max_resource_profiles=2,
        )
        sch = DynamicTaskScheduler(config=cfg, monitor=FakeMonitor([snap(50, 20)]))

        def add_profile(key: str, ts: float) -> None:
            runtime = TaskRuntime(
                spec=TaskSpec(
                    task_id=f"RUNTIME-{key}",
                    command=["python", "-c", "print(1)"],
                    priority=1,
                    estimated_mem_mb=100,
                    estimated_cpu_percent=5,
                ),
                start_ts=0.0,
                state="COMPLETED",
                profile_key=key,
                observed_peak_mem_mb=500.0,
                observed_peak_cpu_pct=10.0,
            )
            sch._update_resource_profile(runtime)
            sch._resource_profiles[key].last_updated_ts = ts

        add_profile("A", 1.0)
        add_profile("B", 2.0)
        add_profile("C", 3.0)
        self.assertEqual(len(sch._resource_profiles), 2)
        self.assertNotIn("A", sch._resource_profiles)
        self.assertIn("B", sch._resource_profiles)
        self.assertIn("C", sch._resource_profiles)

    def test_invalid_profile_config_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad_profile_cfg.json"
            cfg = SchedulerConfig().__dict__.copy()
            cfg["profile_safety_multiplier"] = 0.9
            p.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_scheduler_config(str(p))


if __name__ == "__main__":
    unittest.main()
