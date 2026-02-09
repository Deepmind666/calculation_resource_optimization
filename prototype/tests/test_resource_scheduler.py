from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resource_scheduler import (  # noqa: E402
    DynamicTaskScheduler,
    ResourceSnapshot,
    SchedulerConfig,
    TaskSpec,
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


if __name__ == "__main__":
    unittest.main()
