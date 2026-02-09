from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from resource_scheduler import DynamicTaskScheduler, ResourceSnapshot, SchedulerConfig, TaskSpec


ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
CSV_PATH = FIGURES_DIR / "scheduler_experiment_metrics.csv"
JSON_PATH = FIGURES_DIR / "scheduler_experiment_metrics.json"


class ScriptedMonitor:
    def __init__(self, snapshots: List[ResourceSnapshot]) -> None:
        self.snapshots = snapshots
        self.i = 0

    def sample(self) -> ResourceSnapshot:
        if self.i >= len(self.snapshots):
            return self.snapshots[-1]
        s = self.snapshots[self.i]
        self.i += 1
        return s


def make_snapshot(mem: float, cpu: float, swap: float = 10.0) -> ResourceSnapshot:
    total = 16 * 1024.0
    used = total * mem / 100.0
    avail = max(1.0, total - used)
    return ResourceSnapshot(
        timestamp=0.0,
        cpu_percent=cpu,
        memory_percent=mem,
        memory_used_mb=used,
        memory_total_mb=total,
        memory_available_mb=avail,
        swap_percent=swap,
        gpu_util_percent=None,
        gpu_memory_percent=None,
        gpu_memory_used_mb=None,
        gpu_memory_total_mb=None,
    )


def run_scenario(name: str, snapshots: List[ResourceSnapshot], task_n: int = 10) -> Dict[str, float]:
    cfg = SchedulerConfig(
        max_workers=4,
        min_workers=1,
        dry_run=True,
        preempt_count_per_tick=2,
        reserve_memory_mb=512,
    )
    scheduler = DynamicTaskScheduler(config=cfg, monitor=ScriptedMonitor(snapshots))
    for i in range(task_n):
        scheduler.submit_task(
            TaskSpec(
                task_id=f"{name}-T-{i+1:03d}",
                command=[],
                priority=(i % 6) + 1,
                estimated_mem_mb=400,
                estimated_cpu_percent=10,
                preemptible=True,
                dry_run_ticks=2,
            )
        )

    for _ in range(len(snapshots)):
        scheduler.tick()

    m = scheduler.metrics_dict()
    unique_blocked = {
        evt["payload"]["task_id"]
        for evt in scheduler.events
        if evt.get("event_type") == "TASK_BLOCKED" and isinstance(evt.get("payload"), dict) and "task_id" in evt["payload"]
    }
    submitted = max(1, m["submitted_total"])
    return {
        "scenario": name,
        "submitted_total": float(m["submitted_total"]),
        "started_total": float(m["started_total"]),
        "completed_total": float(m["completed_total"]),
        "blocked_event_total": float(m["blocked_total"]),
        "unique_blocked_tasks": float(len(unique_blocked)),
        "preempted_total": float(m["preempted_total"]),
        "emergency_ticks": float(m["emergency_ticks"]),
        "admission_success_rate": round(m["started_total"] / submitted, 4),
        "preemption_rate": round(m["preempted_total"] / submitted, 4),
    }


def main() -> None:
    scenarios = [
        (
            "normal",
            [make_snapshot(mem=55, cpu=35) for _ in range(10)],
        ),
        (
            "high_pressure",
            [make_snapshot(mem=88, cpu=72) for _ in range(10)],
        ),
        (
            "emergency",
            [make_snapshot(mem=95, cpu=90) for _ in range(10)],
        ),
        (
            "burst_then_recover",
            [make_snapshot(mem=70, cpu=60) for _ in range(3)]
            + [make_snapshot(mem=94, cpu=85) for _ in range(4)]
            + [make_snapshot(mem=68, cpu=40) for _ in range(3)],
        ),
    ]

    rows = [run_scenario(name, snaps) for name, snaps in scenarios]
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"[OK] wrote: {CSV_PATH}")
    print(f"[OK] wrote: {JSON_PATH}")


if __name__ == "__main__":
    main()
