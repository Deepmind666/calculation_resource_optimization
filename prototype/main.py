from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import List

from resource_scheduler import (
    DynamicTaskScheduler,
    SchedulerConfig,
    TaskSpec,
    load_scheduler_config,
)


ROOT = Path(__file__).resolve().parents[1]


def build_demo_tasks(real_run: bool, task_count: int = 8) -> List[TaskSpec]:
    tasks: List[TaskSpec] = []
    for i in range(task_count):
        priority = (i % 6) + 1
        mem = 250 + (i % 4) * 120
        cpu = 8 + (i % 5) * 6

        if real_run:
            duration = 3 + (i % 3)
            # 分配小块内存，避免演示脚本本身造成风险。
            cmd = [
                sys.executable,
                "-c",
                f"import time; x=bytearray({min(mem, 320)}*1024*1024); time.sleep({duration})",
            ]
        else:
            cmd = []

        tasks.append(
            TaskSpec(
                task_id=f"T-{i+1:03d}",
                command=cmd,
                priority=priority,
                estimated_mem_mb=mem,
                estimated_cpu_percent=cpu,
                estimated_gpu_mem_mb=0,
                preemptible=(priority >= 3),
                max_runtime_sec=60,
                dry_run_ticks=2 + (i % 2),
            )
        )
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Dynamic scheduler demo for CPU/GPU/Memory protection.")
    parser.add_argument("--config", default=str(ROOT / "spec" / "scheduler_config.example.json"))
    parser.add_argument("--ticks", type=int, default=12)
    parser.add_argument("--real-run", action="store_true", help="Execute real subprocess tasks.")
    parser.add_argument("--print-events", action="store_true")
    args = parser.parse_args()

    config = load_scheduler_config(args.config)
    if not args.real_run:
        config.dry_run = True

    scheduler = DynamicTaskScheduler(config=config)

    for task in build_demo_tasks(real_run=args.real_run):
        scheduler.submit_task(task)

    reports = []
    try:
        for _ in range(args.ticks):
            report = scheduler.tick()
            reports.append(report)
            print(
                f"[tick={report.tick_id:02d}] mode={report.mode:<9} "
                f"running={report.running_count:<2} pending={report.pending_count:<2} "
                f"started={len(report.started):<2} blocked={len(report.blocked):<2} preempted={len(report.preempted):<2} "
                f"mem={report.snapshot.memory_percent:.1f}% cpu={report.snapshot.cpu_percent:.1f}%"
            )
            time.sleep(config.check_interval_sec)
    finally:
        scheduler.shutdown()

    out = {
        "metrics": scheduler.metrics_dict(),
        "ticks": [
            {
                "tick_id": r.tick_id,
                "mode": r.mode,
                "running_count": r.running_count,
                "pending_count": r.pending_count,
                "started": r.started,
                "blocked": r.blocked,
                "preempted": r.preempted,
            }
            for r in reports
        ],
    }

    out_file = ROOT / "figures" / "scheduler_demo_report.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {out_file}")

    if args.print_events:
        print(scheduler.dump_events_json())


if __name__ == "__main__":
    main()
