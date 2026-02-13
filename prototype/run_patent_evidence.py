from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Type

from resource_scheduler import DynamicTaskScheduler, ResourceSnapshot, SchedulerConfig, TaskSpec


ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
CSV_PATH = FIGURES_DIR / "patent_evidence_metrics.csv"
JSON_PATH = FIGURES_DIR / "patent_evidence_metrics.json"


class ScriptedMonitor:
    def __init__(self, snapshots: List[ResourceSnapshot]) -> None:
        if not snapshots:
            raise ValueError("snapshots must not be empty.")
        self.snapshots = snapshots
        self.i = 0
        self.history: List[ResourceSnapshot] = []

    def sample(self) -> ResourceSnapshot:
        if self.i >= len(self.snapshots):
            s = self.snapshots[-1]
        else:
            s = self.snapshots[self.i]
            self.i += 1
        self.history.append(s)
        return s


def make_snapshot(mem_pct: float, cpu_pct: float, swap_pct: float = 10.0) -> ResourceSnapshot:
    total_mb = 16 * 1024.0
    used_mb = total_mb * mem_pct / 100.0
    avail_mb = max(1.0, total_mb - used_mb)
    return ResourceSnapshot(
        timestamp=0.0,
        cpu_percent=cpu_pct,
        memory_percent=mem_pct,
        memory_used_mb=used_mb,
        memory_total_mb=total_mb,
        memory_available_mb=avail_mb,
        swap_percent=swap_pct,
        gpu_util_percent=None,
        gpu_memory_percent=None,
        gpu_memory_used_mb=None,
        gpu_memory_total_mb=None,
    )


def _count_mode_switches(modes: List[str]) -> int:
    if not modes:
        return 0
    return sum(1 for prev, curr in zip(modes, modes[1:]) if prev != curr)


def _first_true_tick(raw_memory_series: List[float], threshold: float) -> Optional[int]:
    for i, mem_pct in enumerate(raw_memory_series, start=1):
        if mem_pct >= threshold:
            return i
    return None


class EmaOnlyModeScheduler(DynamicTaskScheduler):
    """Ablation baseline: emergency check also uses EMA snapshot (no raw bypass)."""

    def _evaluate_mode(self, s: ResourceSnapshot, raw: Optional[ResourceSnapshot] = None) -> str:
        emergency_view = s
        hysteresis = max(0.0, float(self.config.mode_hysteresis_pct))
        mem_high_exit = max(0.0, self.config.memory_high_pct - hysteresis)
        cpu_high_exit = max(0.0, self.config.cpu_high_pct - hysteresis)
        gpu_high_exit = max(0.0, self.config.gpu_memory_high_pct - hysteresis)

        emergency_trigger = False
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


class NoCumulativeProjectionScheduler(DynamicTaskScheduler):
    """Ablation baseline: each admission uses snapshot-only view in the same tick."""

    def _can_admit(
        self,
        task: TaskSpec,
        s: ResourceSnapshot,
        mode: str,
        planned_extra_mem_mb: float = 0.0,
        planned_extra_cpu_pct: float = 0.0,
        planned_extra_gpu_by_index: dict[int, float] | None = None,
        planned_extra_gpu_unbound_mb: float = 0.0,
        running_est_mem_mb: float | None = None,
        running_est_cpu_pct: float | None = None,
        running_gpu_unbound_mb: float | None = None,
        running_gpu_by_index: dict[int, float] | None = None,
    ) -> tuple[bool, str]:
        return super()._can_admit(
            task,
            s,
            mode,
            planned_extra_mem_mb=0.0,
            planned_extra_cpu_pct=0.0,
            planned_extra_gpu_by_index={},
            planned_extra_gpu_unbound_mb=0.0,
            running_est_mem_mb=running_est_mem_mb,
            running_est_cpu_pct=running_est_cpu_pct,
            running_gpu_unbound_mb=running_gpu_unbound_mb,
            running_gpu_by_index=running_gpu_by_index,
        )


def run_p02_mode_stability_ablation() -> Dict[str, object]:
    # One raw spike sequence where EMA(alpha=0.3) delays emergency crossing.
    raw_memory_series = [82.0, 83.0, 97.0, 97.0, 97.0, 97.0, 83.0, 82.0]
    snapshots = [make_snapshot(mem, cpu_pct=35.0) for mem in raw_memory_series]
    base_cfg = SchedulerConfig(
        dry_run=True,
        max_workers=2,
        min_workers=1,
        reserve_memory_mb=512,
        ema_alpha=0.3,
        mode_hysteresis_pct=3.0,
        emergency_cooldown_ticks=2,
        preempt_count_per_tick=1,
    )
    variants: List[tuple[str, Type[DynamicTaskScheduler]]] = [
        ("dual_view_raw_plus_ema", DynamicTaskScheduler),
        ("ema_only_alpha_0_3_no_raw_bypass", EmaOnlyModeScheduler),
    ]
    raw_emergency_first_tick = _first_true_tick(raw_memory_series, base_cfg.memory_emergency_pct)
    if raw_emergency_first_tick is None:
        raise ValueError("raw emergency trigger is required for P-02 ablation.")

    rows: List[Dict[str, object]] = []
    for name, scheduler_cls in variants:
        monitor = ScriptedMonitor(snapshots)
        scheduler = scheduler_cls(config=base_cfg, monitor=monitor)
        reports = [scheduler.tick() for _ in range(len(snapshots))]
        modes = [r.mode for r in reports]
        first_emergency_tick = None
        for i, mode in enumerate(modes, start=1):
            if mode == "EMERGENCY":
                first_emergency_tick = i
                break
        response_delay_ticks = None
        if first_emergency_tick is not None:
            response_delay_ticks = first_emergency_tick - raw_emergency_first_tick
        m = scheduler.metrics_dict()
        rows.append(
            {
                "variant": name,
                "ticks": len(reports),
                "raw_emergency_first_tick": raw_emergency_first_tick,
                "first_emergency_tick": first_emergency_tick,
                "response_delay_ticks": response_delay_ticks,
                "mode_switches": _count_mode_switches(modes),
                "emergency_ticks": int(m["emergency_ticks"]),
                "modes": modes,
            }
        )

    return {
        "scenario": "P-02 dual-view emergency response delay ablation",
        "raw_memory_series_pct": raw_memory_series,
        "raw_emergency_first_tick": raw_emergency_first_tick,
        "variants": rows,
    }


def _projected_mem_pct(
    base_memory_used_mb: float,
    reserve_memory_mb: int,
    admitted_task_count: int,
    task_mem_mb: int,
    total_memory_mb: float,
) -> float:
    projected_mb = base_memory_used_mb + float(reserve_memory_mb) + float(admitted_task_count * task_mem_mb)
    return 100.0 * projected_mb / max(1.0, total_memory_mb)


def run_p03_cumulative_admission_ablation() -> Dict[str, object]:
    snapshot = make_snapshot(mem_pct=78.0, cpu_pct=20.0)
    task_count = 4
    task_mem_mb = 800
    task_cpu_pct = 5.0
    memory_limit_pct = 92.0
    reserve_memory_mb = 512
    command = [sys.executable, "-c", "import time; time.sleep(0.8)"]

    cfg = SchedulerConfig(
        dry_run=False,
        max_workers=6,
        min_workers=1,
        max_start_per_tick_normal=6,
        max_start_per_tick_high=1,
        reserve_memory_mb=reserve_memory_mb,
        memory_emergency_pct=memory_limit_pct,
        ema_alpha=1.0,
        check_interval_sec=0.05,
        kill_timeout_sec=1.0,
    )
    variants: List[tuple[str, Type[DynamicTaskScheduler]]] = [
        ("with_cumulative_projection", DynamicTaskScheduler),
        ("without_cumulative_projection_baseline", NoCumulativeProjectionScheduler),
    ]

    variant_rows: List[Dict[str, object]] = []
    for variant_name, scheduler_cls in variants:
        monitor = ScriptedMonitor([snapshot])
        scheduler = scheduler_cls(config=cfg, monitor=monitor)
        for i in range(task_count):
            scheduler.submit_task(
                TaskSpec(
                    task_id=f"P03-{variant_name}-T-{i + 1:03d}",
                    command=command,
                    priority=1,
                    estimated_mem_mb=task_mem_mb,
                    estimated_cpu_percent=task_cpu_pct,
                    preemptible=True,
                    dry_run_ticks=5,
                )
            )
        report = scheduler.tick()
        admitted_tasks = len(report.started)
        projected_peak_memory_pct = _projected_mem_pct(
            base_memory_used_mb=snapshot.memory_used_mb,
            reserve_memory_mb=reserve_memory_mb,
            admitted_task_count=admitted_tasks,
            task_mem_mb=task_mem_mb,
            total_memory_mb=snapshot.memory_total_mb,
        )
        variant_rows.append(
            {
                "variant": variant_name,
                "admitted_tasks": admitted_tasks,
                "blocked_tasks": len(report.blocked),
                "projected_peak_memory_pct": round(projected_peak_memory_pct, 4),
                "breach_limit": projected_peak_memory_pct >= memory_limit_pct,
            }
        )
        scheduler.shutdown()

    with_cumulative = next(r for r in variant_rows if r["variant"] == "with_cumulative_projection")
    without_cumulative = next(r for r in variant_rows if r["variant"] == "without_cumulative_projection_baseline")
    over_issued_tasks = max(0, int(without_cumulative["admitted_tasks"]) - int(with_cumulative["admitted_tasks"]))
    over_issue_rate = over_issued_tasks / float(task_count)

    return {
        "scenario": "P-03 same-tick cumulative projection ablation",
        "snapshot_memory_pct": snapshot.memory_percent,
        "memory_limit_pct": memory_limit_pct,
        "task_count": task_count,
        "task_mem_mb": task_mem_mb,
        "over_issued_tasks_without_cumulative": over_issued_tasks,
        "over_issue_rate_without_cumulative": round(over_issue_rate, 4),
        "variants": variant_rows,
    }


def build_flattened_rows(p02: Dict[str, object], p03: Dict[str, object]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item in p02["variants"]:  # type: ignore[index]
        variant = item["variant"]  # type: ignore[index]
        rows.append(
            {
                "evidence_id": "P-02",
                "scenario": p02["scenario"],  # type: ignore[index]
                "variant": variant,
                "raw_emergency_first_tick": item["raw_emergency_first_tick"],  # type: ignore[index]
                "first_emergency_tick": item["first_emergency_tick"],  # type: ignore[index]
                "response_delay_ticks": item["response_delay_ticks"],  # type: ignore[index]
                "mode_switches": item["mode_switches"],  # type: ignore[index]
                "emergency_ticks": item["emergency_ticks"],  # type: ignore[index]
            }
        )

    for item in p03["variants"]:  # type: ignore[index]
        rows.append(
            {
                "evidence_id": "P-03",
                "scenario": p03["scenario"],  # type: ignore[index]
                "variant": item["variant"],  # type: ignore[index]
                "admitted_tasks": item["admitted_tasks"],  # type: ignore[index]
                "blocked_tasks": item["blocked_tasks"],  # type: ignore[index]
                "projected_peak_memory_pct": item["projected_peak_memory_pct"],  # type: ignore[index]
                "memory_limit_pct": p03["memory_limit_pct"],  # type: ignore[index]
                "breach_limit": item["breach_limit"],  # type: ignore[index]
                "over_issued_tasks_without_cumulative": p03["over_issued_tasks_without_cumulative"],  # type: ignore[index]
                "over_issue_rate_without_cumulative": p03["over_issue_rate_without_cumulative"],  # type: ignore[index]
            }
        )
    return rows


def main() -> None:
    p02 = run_p02_mode_stability_ablation()
    p03 = run_p03_cumulative_admission_ablation()
    rows = build_flattened_rows(p02, p03)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "p02_mode_stability_ablation": p02,
        "p03_cumulative_admission_ablation": p03,
    }
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[OK] wrote: {CSV_PATH}")
    print(f"[OK] wrote: {JSON_PATH}")


if __name__ == "__main__":
    main()
