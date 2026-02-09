from __future__ import annotations

from pathlib import Path
import sys
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
        cfg = SchedulerConfig(dry_run=True)
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
        cfg = SchedulerConfig(dry_run=True, preempt_count_per_tick=2)
        monitor = FakeMonitor([snap(60, 20), snap(96, 70)])
        sch = DynamicTaskScheduler(config=cfg, monitor=monitor)

        sch.submit_task(TaskSpec("A", [], priority=5, estimated_mem_mb=100, estimated_cpu_percent=2, dry_run_ticks=5))
        sch.submit_task(TaskSpec("B", [], priority=6, estimated_mem_mb=100, estimated_cpu_percent=2, dry_run_ticks=5))
        first = sch.tick()
        self.assertGreaterEqual(len(first.started), 1)

        second = sch.tick()
        self.assertEqual(second.mode, "EMERGENCY")
        self.assertGreaterEqual(len(second.preempted), 1)


if __name__ == "__main__":
    unittest.main()
