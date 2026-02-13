from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import json
import random
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

from resource_scheduler import (  # noqa: E402
    DynamicTaskScheduler,
    ResourceMonitor,
    ResourceSnapshot,
    SchedulerConfig,
    TaskRuntime,
    TaskSpec,
)


ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
CSV_PATH = FIGURES_DIR / "advanced_research_metrics.csv"
JSON_PATH = FIGURES_DIR / "advanced_research_metrics.json"


def make_snapshot(
    mem_pct: float,
    cpu_pct: float,
    *,
    swap_pct: float = 10.0,
    total_mem_mb: float = 16 * 1024.0,
    gpu_cards: Optional[List[Dict[str, float]]] = None,
) -> ResourceSnapshot:
    used_mb = total_mem_mb * mem_pct / 100.0
    avail_mb = max(1.0, total_mem_mb - used_mb)
    gpu_used_mb: Optional[float] = None
    gpu_total_mb: Optional[float] = None
    gpu_pct: Optional[float] = None
    if gpu_cards:
        hottest = max(gpu_cards, key=lambda x: float(x["memory_percent"]))
        gpu_used_mb = float(hottest["used_mb"])
        gpu_total_mb = float(hottest["total_mb"])
        gpu_pct = float(hottest["memory_percent"])
    return ResourceSnapshot(
        timestamp=time.time(),
        cpu_percent=cpu_pct,
        memory_percent=mem_pct,
        memory_used_mb=used_mb,
        memory_total_mb=total_mem_mb,
        memory_available_mb=avail_mb,
        swap_percent=swap_pct,
        gpu_util_percent=None,
        gpu_memory_percent=gpu_pct,
        gpu_memory_used_mb=gpu_used_mb,
        gpu_memory_total_mb=gpu_total_mb,
        gpu_cards=gpu_cards,
    )


class StaticMonitor:
    def __init__(self, snapshot: ResourceSnapshot) -> None:
        self.snapshot = snapshot

    def sample(self) -> ResourceSnapshot:
        return self.snapshot


class AggregateGpuProjectionScheduler(DynamicTaskScheduler):
    """Ablation baseline for P-04: collapse all GPU budgets into one aggregate bucket."""

    def _can_admit(
        self,
        task: TaskSpec,
        s: ResourceSnapshot,
        mode: str,
        planned_extra_mem_mb: float = 0.0,
        planned_extra_cpu_pct: float = 0.0,
        planned_extra_gpu_by_index: Optional[Dict[int, float]] = None,
        planned_extra_gpu_unbound_mb: float = 0.0,
        running_est_mem_mb: Optional[float] = None,
        running_est_cpu_pct: Optional[float] = None,
        running_gpu_unbound_mb: Optional[float] = None,
        running_gpu_by_index: Optional[Dict[int, float]] = None,
    ) -> Tuple[bool, str]:
        if task.target_gpu_index is None or not s.gpu_cards:
            return super()._can_admit(
                task,
                s,
                mode,
                planned_extra_mem_mb=planned_extra_mem_mb,
                planned_extra_cpu_pct=planned_extra_cpu_pct,
                planned_extra_gpu_by_index=planned_extra_gpu_by_index,
                planned_extra_gpu_unbound_mb=planned_extra_gpu_unbound_mb,
                running_est_mem_mb=running_est_mem_mb,
                running_est_cpu_pct=running_est_cpu_pct,
                running_gpu_unbound_mb=running_gpu_unbound_mb,
                running_gpu_by_index=running_gpu_by_index,
            )

        target = int(task.target_gpu_index)
        if target < 0 or target >= len(s.gpu_cards):
            return False, f"target gpu unavailable ({target})"
        target_used = float(s.gpu_cards[target]["used_mb"])
        target_cap = float(s.gpu_cards[target]["total_mb"])
        aggregate_pct = 100.0 * target_used / max(1.0, target_cap)
        aggregate_snapshot = replace(
            s,
            gpu_memory_used_mb=target_used,
            gpu_memory_total_mb=target_cap,
            gpu_memory_percent=aggregate_pct,
        )
        aggregate_task = replace(task, target_gpu_index=None)
        aggregate_unbound = float(planned_extra_gpu_unbound_mb) + sum(
            float(v) for v in (planned_extra_gpu_by_index or {}).values()
        )
        return super()._can_admit(
            aggregate_task,
            aggregate_snapshot,
            mode,
            planned_extra_mem_mb=planned_extra_mem_mb,
            planned_extra_cpu_pct=planned_extra_cpu_pct,
            planned_extra_gpu_by_index={},
            planned_extra_gpu_unbound_mb=aggregate_unbound,
            running_est_mem_mb=running_est_mem_mb,
            running_est_cpu_pct=running_est_cpu_pct,
            running_gpu_unbound_mb=running_gpu_unbound_mb,
            running_gpu_by_index=running_gpu_by_index,
        )


def run_p04_per_gpu_affinity_ablation(trials: int = 4000, seed: int = 20260211) -> Dict[str, object]:
    rng = random.Random(seed)
    cfg = SchedulerConfig(
        dry_run=False,
        memory_emergency_pct=92.0,
        cpu_hard_pct=95.0,
        gpu_memory_emergency_pct=95.0,
        reserve_memory_mb=512,
        enable_gpu_guard=True,
    )
    base_snapshot = make_snapshot(40.0, 20.0)
    per_gpu_scheduler = DynamicTaskScheduler(cfg, monitor=StaticMonitor(base_snapshot))
    aggregate_scheduler = AggregateGpuProjectionScheduler(cfg, monitor=StaticMonitor(base_snapshot))

    aggregate_false_blocks = 0
    per_gpu_false_blocks = 0
    per_gpu_admit = 0
    aggregate_admit = 0
    oracle_safe = 0
    scenario_stats: Dict[str, Dict[str, float]] = {
        "other_card_only": {
            "trials": 0.0,
            "safe_cases": 0.0,
            "per_gpu_admit": 0.0,
            "aggregate_admit": 0.0,
            "per_gpu_false_blocks": 0.0,
            "aggregate_false_blocks": 0.0,
        },
        "same_card_only": {
            "trials": 0.0,
            "safe_cases": 0.0,
            "per_gpu_admit": 0.0,
            "aggregate_admit": 0.0,
            "per_gpu_false_blocks": 0.0,
            "aggregate_false_blocks": 0.0,
        },
        "mixed_cards": {
            "trials": 0.0,
            "safe_cases": 0.0,
            "per_gpu_admit": 0.0,
            "aggregate_admit": 0.0,
            "per_gpu_false_blocks": 0.0,
            "aggregate_false_blocks": 0.0,
        },
        "no_planned_budget": {
            "trials": 0.0,
            "safe_cases": 0.0,
            "per_gpu_admit": 0.0,
            "aggregate_admit": 0.0,
            "per_gpu_false_blocks": 0.0,
            "aggregate_false_blocks": 0.0,
        },
    }

    for i in range(trials):
        total_gpu_mb = float(rng.choice([8192, 10240, 12288, 16384]))
        target_used = total_gpu_mb * rng.uniform(0.48, 0.86)
        other_used = total_gpu_mb * rng.uniform(0.05, 0.42)
        target_task_gpu = float(rng.randint(256, 1800))
        scenario = rng.choice(
            [
                "other_card_only",
                "same_card_only",
                "mixed_cards",
                "no_planned_budget",
            ]
        )
        planned_target_card = 0.0
        planned_other_card = 0.0
        if scenario == "other_card_only":
            planned_other_card = float(rng.randint(600, 2600))
        elif scenario == "same_card_only":
            planned_target_card = float(rng.randint(300, 1600))
        elif scenario == "mixed_cards":
            planned_target_card = float(rng.randint(200, 1200))
            planned_other_card = float(rng.randint(400, 1800))
        planned_unbound = float(rng.choice([0, 0, 200, 400, 800]))

        cards = [
            {
                "index": 0.0,
                "memory_percent": 100.0 * target_used / total_gpu_mb,
                "util_percent": 50.0,
                "used_mb": target_used,
                "total_mb": total_gpu_mb,
            },
            {
                "index": 1.0,
                "memory_percent": 100.0 * other_used / total_gpu_mb,
                "util_percent": 30.0,
                "used_mb": other_used,
                "total_mb": total_gpu_mb,
            },
        ]
        snapshot = make_snapshot(45.0, 25.0, gpu_cards=cards)
        task = TaskSpec(
            task_id=f"P04-T-{i:05d}",
            command=[sys.executable, "-c", "print('noop')"],
            priority=2,
            estimated_mem_mb=256,
            estimated_cpu_percent=5.0,
            estimated_gpu_mem_mb=int(target_task_gpu),
            target_gpu_index=0,
            preemptible=True,
            max_runtime_sec=10.0,
        )
        projected_target_pct = (
            100.0 * (target_used + planned_target_card + planned_unbound + target_task_gpu) / total_gpu_mb
        )
        safe_on_target = projected_target_pct < cfg.gpu_memory_emergency_pct
        bucket = scenario_stats[scenario]
        bucket["trials"] += 1.0
        if safe_on_target:
            oracle_safe += 1
            bucket["safe_cases"] += 1.0

        planned_by_index = {0: planned_target_card, 1: planned_other_card}
        ok_per_gpu, _ = per_gpu_scheduler._can_admit(
            task,
            snapshot,
            "NORMAL",
            planned_extra_gpu_by_index=planned_by_index,
            planned_extra_gpu_unbound_mb=planned_unbound,
        )
        ok_aggregate, _ = aggregate_scheduler._can_admit(
            task,
            snapshot,
            "NORMAL",
            planned_extra_gpu_by_index=planned_by_index,
            planned_extra_gpu_unbound_mb=planned_unbound,
        )
        if ok_per_gpu:
            per_gpu_admit += 1
            bucket["per_gpu_admit"] += 1.0
        if ok_aggregate:
            aggregate_admit += 1
            bucket["aggregate_admit"] += 1.0
        if safe_on_target and not ok_per_gpu:
            per_gpu_false_blocks += 1
            bucket["per_gpu_false_blocks"] += 1.0
        if safe_on_target and not ok_aggregate:
            aggregate_false_blocks += 1
            bucket["aggregate_false_blocks"] += 1.0

    safe_denom = max(1, oracle_safe)
    scenario_breakdown: Dict[str, Dict[str, float]] = {}
    for name, stats in scenario_stats.items():
        local_safe = max(1.0, stats["safe_cases"])
        scenario_breakdown[name] = {
            "trials": int(stats["trials"]),
            "safe_cases": int(stats["safe_cases"]),
            "per_gpu_admit": int(stats["per_gpu_admit"]),
            "aggregate_admit": int(stats["aggregate_admit"]),
            "per_gpu_false_blocks": int(stats["per_gpu_false_blocks"]),
            "aggregate_false_blocks": int(stats["aggregate_false_blocks"]),
            "per_gpu_false_block_rate": round(stats["per_gpu_false_blocks"] / local_safe, 6),
            "aggregate_false_block_rate": round(stats["aggregate_false_blocks"] / local_safe, 6),
            "false_block_reduction": round(
                (stats["aggregate_false_blocks"] - stats["per_gpu_false_blocks"]) / local_safe,
                6,
            ),
        }
    return {
        "evidence_id": "P-04",
        "scenario": "per_gpu_affinity_admission_ablation",
        "trials": trials,
        "safe_cases": oracle_safe,
        "per_gpu_admit": per_gpu_admit,
        "aggregate_admit": aggregate_admit,
        "per_gpu_false_blocks": per_gpu_false_blocks,
        "aggregate_false_blocks": aggregate_false_blocks,
        "per_gpu_false_block_rate": round(per_gpu_false_blocks / safe_denom, 6),
        "aggregate_false_block_rate": round(aggregate_false_blocks / safe_denom, 6),
        "false_block_reduction": round(
            (aggregate_false_blocks - per_gpu_false_blocks) / safe_denom,
            6,
        ),
        "scenario_breakdown": scenario_breakdown,
    }


def _effective_gpu_reclaim(runtime: TaskRuntime, hottest_gpu_index: Optional[int]) -> float:
    gpu_mb = float(runtime.spec.estimated_gpu_mem_mb)
    if gpu_mb <= 0:
        return 0.0
    if runtime.spec.target_gpu_index is None:
        return gpu_mb * 0.5
    if hottest_gpu_index is None or runtime.spec.target_gpu_index == hottest_gpu_index:
        return gpu_mb
    return gpu_mb * 0.1


def _simulate_preemption_baseline(
    runtimes: Sequence[TaskRuntime],
    *,
    strategy: str,
    reclaim_needed_mb: float,
    reclaim_needed_gpu_mb: float,
    hottest_gpu_index: Optional[int],
    preempt_limit: int,
    rng: random.Random,
) -> Tuple[int, float, float]:
    mem_denom = max(1.0, reclaim_needed_mb)
    gpu_denom = max(1.0, reclaim_needed_gpu_mb)

    def score(runtime: TaskRuntime) -> float:
        mem_val = float(runtime.spec.estimated_mem_mb)
        gpu_val = _effective_gpu_reclaim(runtime, hottest_gpu_index)
        if strategy == "raw_mb":
            return mem_val + gpu_val
        if strategy == "random":
            return rng.random()
        return mem_val / mem_denom + gpu_val / gpu_denom

    candidates = list(runtimes)
    candidates.sort(
        key=lambda r: (
            r.spec.priority,
            score(r),
            -r.start_ts,
        ),
        reverse=True,
    )
    k = min(preempt_limit, len(candidates))
    reclaimed_mem = 0.0
    reclaimed_gpu = 0.0
    preempted = 0
    for i in range(k):
        runtime = candidates[i]
        preempted += 1
        reclaimed_mem += float(runtime.spec.estimated_mem_mb)
        reclaimed_gpu += _effective_gpu_reclaim(runtime, hottest_gpu_index)
        mem_goal_done = reclaim_needed_mb <= 0.0 or reclaimed_mem >= reclaim_needed_mb
        gpu_goal_done = reclaim_needed_gpu_mb <= 0.0 or reclaimed_gpu >= reclaim_needed_gpu_mb
        if mem_goal_done and gpu_goal_done:
            break
    return preempted, reclaimed_mem, reclaimed_gpu


def _run_normalized_scheduler_trial(
    runtimes: Sequence[TaskRuntime],
    snapshot: ResourceSnapshot,
    *,
    preempt_limit: int,
) -> Tuple[int, float, float]:
    cfg = SchedulerConfig(
        dry_run=False,
        preempt_count_per_tick=preempt_limit,
        preempt_sort_key="oldest_first",
        memory_high_pct=85.0,
        memory_emergency_pct=92.0,
        gpu_memory_high_pct=85.0,
        gpu_memory_emergency_pct=95.0,
        reserve_memory_mb=512,
        enable_gpu_guard=True,
    )
    scheduler = DynamicTaskScheduler(cfg, monitor=StaticMonitor(snapshot))
    runtime_map: Dict[str, TaskRuntime] = {}
    for runtime in runtimes:
        runtime_map[runtime.spec.task_id] = TaskRuntime(
            spec=runtime.spec,
            start_ts=runtime.start_ts,
            state="RUNNING",
            process=None,
        )
    scheduler.running = runtime_map
    preempted_ids = scheduler._preempt_low_priority(snapshot, raw_snapshot=snapshot)
    by_id = {runtime.spec.task_id: runtime for runtime in runtimes}
    reclaimed_mem = sum(float(by_id[tid].spec.estimated_mem_mb) for tid in preempted_ids)
    reclaimed_gpu = sum(_effective_gpu_reclaim(by_id[tid], hottest_gpu_index=0) for tid in preempted_ids)
    return len(preempted_ids), reclaimed_mem, reclaimed_gpu


def _run_p05_variant(
    *,
    trials: int,
    seed: int,
    preempt_limit: Optional[int],
) -> Dict[str, float]:
    rng = random.Random(seed)
    normalized_preemptions: List[int] = []
    raw_preemptions: List[int] = []
    random_preemptions: List[int] = []
    normalized_recovery = 0
    raw_recovery = 0
    random_recovery = 0
    norm_better_than_raw = 0
    norm_better_than_random = 0

    for i in range(trials):
        total_mem_mb = float(rng.choice([16384, 24576, 32768]))
        used_mem_pct = rng.uniform(92.0, 94.0)
        used_mem_mb = total_mem_mb * used_mem_pct / 100.0
        total_gpu_mb = float(rng.choice([8192, 12288, 16384]))
        used_gpu_pct = rng.uniform(97.0, 99.0)
        used_gpu_mb = total_gpu_mb * used_gpu_pct / 100.0
        cards = [
            {
                "index": 0.0,
                "memory_percent": used_gpu_pct,
                "util_percent": 70.0,
                "used_mb": used_gpu_mb,
                "total_mb": total_gpu_mb,
            }
        ]
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=50.0,
            memory_percent=used_mem_pct,
            memory_used_mb=used_mem_mb,
            memory_total_mb=total_mem_mb,
            memory_available_mb=max(1.0, total_mem_mb - used_mem_mb),
            swap_percent=20.0,
            gpu_util_percent=70.0,
            gpu_memory_percent=used_gpu_pct,
            gpu_memory_used_mb=used_gpu_mb,
            gpu_memory_total_mb=total_gpu_mb,
            gpu_cards=cards,
        )

        runtimes: List[TaskRuntime] = []
        now = time.time()
        for j in range(24):
            bucket = rng.random()
            if bucket < 0.34:
                mem_mb = rng.randint(2000, 3400)
                gpu_mb = rng.randint(50, 220)
            elif bucket < 0.68:
                mem_mb = rng.randint(120, 520)
                gpu_mb = rng.randint(1000, 2200)
            else:
                mem_mb = rng.randint(700, 1500)
                gpu_mb = rng.randint(300, 900)
            spec = TaskSpec(
                task_id=f"P05-{i:05d}-{j:02d}",
                command=[sys.executable, "-c", "print('noop')"],
                priority=rng.randint(1, 6),
                estimated_mem_mb=mem_mb,
                estimated_cpu_percent=float(rng.randint(5, 40)),
                estimated_gpu_mem_mb=gpu_mb,
                target_gpu_index=0 if rng.random() < 0.85 else None,
                preemptible=True,
                max_runtime_sec=60.0,
            )
            runtimes.append(TaskRuntime(spec=spec, start_ts=now - float(j * 3 + rng.randint(0, 2)), state="RUNNING"))

        target_mem_mb = (total_mem_mb * 85.0 / 100.0) - 512.0
        reclaim_needed_mb = max(0.0, used_mem_mb - target_mem_mb)
        target_gpu_mb = total_gpu_mb * 85.0 / 100.0
        reclaim_needed_gpu_mb = max(0.0, used_gpu_mb - target_gpu_mb)
        active_preempt_limit = len(runtimes) if preempt_limit is None else max(1, min(preempt_limit, len(runtimes)))

        n_count, n_mem, n_gpu = _run_normalized_scheduler_trial(
            runtimes,
            snapshot,
            preempt_limit=active_preempt_limit,
        )
        r_count, r_mem, r_gpu = _simulate_preemption_baseline(
            runtimes,
            strategy="raw_mb",
            reclaim_needed_mb=reclaim_needed_mb,
            reclaim_needed_gpu_mb=reclaim_needed_gpu_mb,
            hottest_gpu_index=0,
            preempt_limit=active_preempt_limit,
            rng=rng,
        )
        x_count, x_mem, x_gpu = _simulate_preemption_baseline(
            runtimes,
            strategy="random",
            reclaim_needed_mb=reclaim_needed_mb,
            reclaim_needed_gpu_mb=reclaim_needed_gpu_mb,
            hottest_gpu_index=0,
            preempt_limit=active_preempt_limit,
            rng=rng,
        )

        normalized_preemptions.append(n_count)
        raw_preemptions.append(r_count)
        random_preemptions.append(x_count)

        if n_mem >= reclaim_needed_mb and n_gpu >= reclaim_needed_gpu_mb:
            normalized_recovery += 1
        if r_mem >= reclaim_needed_mb and r_gpu >= reclaim_needed_gpu_mb:
            raw_recovery += 1
        if x_mem >= reclaim_needed_mb and x_gpu >= reclaim_needed_gpu_mb:
            random_recovery += 1

        if n_count <= r_count:
            norm_better_than_raw += 1
        if n_count <= x_count:
            norm_better_than_random += 1

    t = max(1, trials)
    resolved_limit = float(preempt_limit if preempt_limit is not None else -1)
    return {
        "preempt_limit": resolved_limit,
        "avg_preemptions_normalized": round(statistics.fmean(normalized_preemptions), 4),
        "avg_preemptions_raw_mb": round(statistics.fmean(raw_preemptions), 4),
        "avg_preemptions_random": round(statistics.fmean(random_preemptions), 4),
        "recovery_rate_normalized": round(normalized_recovery / t, 6),
        "recovery_rate_raw_mb": round(raw_recovery / t, 6),
        "recovery_rate_random": round(random_recovery / t, 6),
        "normalized_better_or_equal_raw_rate": round(norm_better_than_raw / t, 6),
        "normalized_better_or_equal_random_rate": round(norm_better_than_random / t, 6),
    }


def run_p05_preemption_ablation(
    trials: int = 4000,
    seed: int = 20260211,
    tight_preempt_limit: int = 5,
) -> Dict[str, object]:
    if tight_preempt_limit < 1:
        raise ValueError("tight_preempt_limit must be >= 1")
    full = _run_p05_variant(trials=trials, seed=seed, preempt_limit=None)
    tight = _run_p05_variant(trials=trials, seed=seed + 17, preempt_limit=tight_preempt_limit)
    return {
        "evidence_id": "P-05",
        "scenario": "normalized_preemption_ablation",
        "trials": trials,
        "avg_preemptions_normalized": full["avg_preemptions_normalized"],
        "avg_preemptions_raw_mb": full["avg_preemptions_raw_mb"],
        "avg_preemptions_random": full["avg_preemptions_random"],
        "recovery_rate_normalized": full["recovery_rate_normalized"],
        "recovery_rate_raw_mb": full["recovery_rate_raw_mb"],
        "recovery_rate_random": full["recovery_rate_random"],
        "normalized_better_or_equal_raw_rate": full["normalized_better_or_equal_raw_rate"],
        "normalized_better_or_equal_random_rate": full["normalized_better_or_equal_random_rate"],
        "tight_preempt_limit": tight_preempt_limit,
        "avg_preemptions_normalized_tight": tight["avg_preemptions_normalized"],
        "avg_preemptions_raw_mb_tight": tight["avg_preemptions_raw_mb"],
        "avg_preemptions_random_tight": tight["avg_preemptions_random"],
        "recovery_rate_normalized_tight": tight["recovery_rate_normalized"],
        "recovery_rate_raw_mb_tight": tight["recovery_rate_raw_mb"],
        "recovery_rate_random_tight": tight["recovery_rate_random"],
        "normalized_better_or_equal_raw_rate_tight": tight["normalized_better_or_equal_raw_rate"],
        "normalized_better_or_equal_random_rate_tight": tight["normalized_better_or_equal_random_rate"],
        "tight_recovery_advantage_vs_raw": round(
            tight["recovery_rate_normalized"] - tight["recovery_rate_raw_mb"],
            6,
        ),
        "tight_recovery_advantage_vs_random": round(
            tight["recovery_rate_normalized"] - tight["recovery_rate_random"],
            6,
        ),
    }


def _mean_ci95(values: Sequence[float]) -> Dict[str, float]:
    if not values:
        raise ValueError("values must be non-empty")
    n = len(values)
    mean = float(statistics.fmean(values))
    stddev = float(statistics.stdev(values)) if n > 1 else 0.0
    ci95_half = 1.96 * stddev / max(1.0, (n ** 0.5))
    return {
        "n": float(n),
        "mean": round(mean, 6),
        "stddev": round(stddev, 6),
        "ci95_low": round(mean - ci95_half, 6),
        "ci95_high": round(mean + ci95_half, 6),
        "min": round(float(min(values)), 6),
        "max": round(float(max(values)), 6),
    }


def _mean_ci95_optional(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return {
            "n": 0.0,
            "mean": None,
            "stddev": None,
            "ci95_low": None,
            "ci95_high": None,
            "min": None,
            "max": None,
        }
    out = _mean_ci95(clean)
    return {
        "n": out["n"],
        "mean": out["mean"],
        "stddev": out["stddev"],
        "ci95_low": out["ci95_low"],
        "ci95_high": out["ci95_high"],
        "min": out["min"],
        "max": out["max"],
    }


def run_multiseed_confidence_summary(
    *,
    trials_per_seed: int = 4000,
    seed_runs: int = 7,
    base_seed: int = 20260211,
    seed_step: int = 9973,
    tight_preempt_limit: int = 5,
) -> Dict[str, object]:
    if trials_per_seed < 1:
        raise ValueError("trials_per_seed must be >= 1")
    if seed_runs < 2:
        raise ValueError("seed_runs must be >= 2")
    if seed_step < 1:
        raise ValueError("seed_step must be >= 1")

    seed_list: List[int] = []
    per_seed: List[Dict[str, object]] = []
    p04_false_block_reduction: List[float] = []
    p04_aggregate_false_block_rate: List[float] = []
    p05_tight_recovery_adv_vs_raw: List[float] = []
    p05_tight_recovery_adv_vs_random: List[float] = []
    p05_tight_recovery_rate_normalized: List[float] = []
    p05_tight_avg_preemptions_normalized: List[float] = []

    for idx in range(seed_runs):
        seed = int(base_seed + idx * seed_step)
        seed_list.append(seed)
        p04 = run_p04_per_gpu_affinity_ablation(trials=trials_per_seed, seed=seed)
        p05 = run_p05_preemption_ablation(
            trials=trials_per_seed,
            seed=seed,
            tight_preempt_limit=tight_preempt_limit,
        )
        row = {
            "seed": seed,
            "p04_false_block_reduction": float(p04["false_block_reduction"]),
            "p04_aggregate_false_block_rate": float(p04["aggregate_false_block_rate"]),
            "p05_tight_recovery_advantage_vs_raw": float(p05["tight_recovery_advantage_vs_raw"]),
            "p05_tight_recovery_advantage_vs_random": float(p05["tight_recovery_advantage_vs_random"]),
            "p05_recovery_rate_normalized_tight": float(p05["recovery_rate_normalized_tight"]),
            "p05_avg_preemptions_normalized_tight": float(p05["avg_preemptions_normalized_tight"]),
        }
        per_seed.append(row)

        p04_false_block_reduction.append(float(row["p04_false_block_reduction"]))
        p04_aggregate_false_block_rate.append(float(row["p04_aggregate_false_block_rate"]))
        p05_tight_recovery_adv_vs_raw.append(float(row["p05_tight_recovery_advantage_vs_raw"]))
        p05_tight_recovery_adv_vs_random.append(float(row["p05_tight_recovery_advantage_vs_random"]))
        p05_tight_recovery_rate_normalized.append(float(row["p05_recovery_rate_normalized_tight"]))
        p05_tight_avg_preemptions_normalized.append(float(row["p05_avg_preemptions_normalized_tight"]))

    return {
        "seed_runs": seed_runs,
        "trials_per_seed": trials_per_seed,
        "base_seed": base_seed,
        "seed_step": seed_step,
        "seed_list": seed_list,
        "metrics": {
            "p04_false_block_reduction": _mean_ci95(p04_false_block_reduction),
            "p04_aggregate_false_block_rate": _mean_ci95(p04_aggregate_false_block_rate),
            "p05_tight_recovery_advantage_vs_raw": _mean_ci95(p05_tight_recovery_adv_vs_raw),
            "p05_tight_recovery_advantage_vs_random": _mean_ci95(p05_tight_recovery_adv_vs_random),
            "p05_recovery_rate_normalized_tight": _mean_ci95(p05_tight_recovery_rate_normalized),
            "p05_avg_preemptions_normalized_tight": _mean_ci95(p05_tight_avg_preemptions_normalized),
        },
        "per_seed": per_seed,
    }


def _sample_gpu_peak_percent() -> Optional[float]:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=1.0,
        )
        peak = None
        for line in out.strip().splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                used = float(parts[0].split()[0])
                total = float(parts[1].split()[0])
            except Exception:
                continue
            if total < 1.0:
                # Discard malformed rows with near-zero or invalid capacity.
                continue
            pct = 100.0 * used / total
            if pct < 0.0 or pct > 1000.0:
                # Ignore absurd ratios from broken driver output/parsing noise.
                continue
            pct = max(0.0, min(100.0, pct))
            peak = pct if peak is None else max(peak, pct)
        return peak
    except Exception:
        return None


class PeakSampler:
    def __init__(self, interval_sec: float = 0.1) -> None:
        self.interval_sec = interval_sec
        self.peak_memory_pct: Optional[float] = None
        self.peak_swap_pct: Optional[float] = None
        self.peak_gpu_memory_pct: Optional[float] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            if psutil is not None:
                vm = psutil.virtual_memory()
                sm = psutil.swap_memory()
                mem_pct = float(vm.percent)
                swap_pct = float(sm.percent)
                self.peak_memory_pct = mem_pct if self.peak_memory_pct is None else max(self.peak_memory_pct, mem_pct)
                self.peak_swap_pct = swap_pct if self.peak_swap_pct is None else max(self.peak_swap_pct, swap_pct)
            gpu = _sample_gpu_peak_percent()
            if gpu is not None:
                if self.peak_gpu_memory_pct is None:
                    self.peak_gpu_memory_pct = gpu
                else:
                    self.peak_gpu_memory_pct = max(self.peak_gpu_memory_pct, gpu)
            time.sleep(self.interval_sec)

    def __enter__(self) -> "PeakSampler":
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


class CpuCappedMonitor:
    """Experiment-only monitor wrapper to de-bias extreme host CPU saturation noise."""

    def __init__(self, *, cpu_cap_pct: float = 99.0, enable_gpu: bool = True) -> None:
        self.inner = ResourceMonitor(enable_gpu=enable_gpu)
        self.cpu_cap_pct = max(1.0, min(100.0, float(cpu_cap_pct)))
        self.clipped_samples = 0

    def sample(self) -> ResourceSnapshot:
        raw = self.inner.sample()
        if raw.cpu_percent <= self.cpu_cap_pct:
            return raw
        self.clipped_samples += 1
        return replace(raw, cpu_percent=self.cpu_cap_pct)


def _round_opt(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, 4)


def _worker_command(mem_mb: int, duration_sec: float, loop_scale: int) -> List[str]:
    code = (
        "import time\n"
        f"buf=bytearray({mem_mb}*1024*1024)\n"
        "x=0\n"
        f"end=time.time()+{duration_sec}\n"
        "while time.time() < end:\n"
        f"    x=(x+sum(i*i for i in range({loop_scale})))%1000003\n"
        "print(len(buf)+x)\n"
    )
    return [sys.executable, "-c", code]


def _detect_host_total_mem_mb() -> float:
    if psutil is not None:
        try:
            vm = psutil.virtual_memory()
            return max(1024.0, float(vm.total) / (1024.0 * 1024.0))
        except Exception:
            pass
    return 16384.0


def plan_real_baseline_params(
    *,
    task_count: int,
    duration_sec: float,
    base_mem_mb: int,
    fixed_workers: int,
    host_total_mem_mb: Optional[float] = None,
) -> Dict[str, object]:
    host_mem_mb = max(1024.0, float(host_total_mem_mb if host_total_mem_mb is not None else _detect_host_total_mem_mb()))
    notes: List[str] = []

    workers = max(1, int(fixed_workers))
    min_task_count = max(4, workers + 1)
    adjusted_task_count = max(int(task_count), min_task_count)
    if adjusted_task_count != int(task_count):
        notes.append(f"task_count raised to minimum {adjusted_task_count} for scheduler observability")

    adjusted_duration_sec = max(float(duration_sec), 6.0)
    if adjusted_duration_sec != float(duration_sec):
        notes.append(f"duration_sec raised to {adjusted_duration_sec:.1f}s to increase tick coverage")

    if host_mem_mb >= 16384.0:
        base_floor_mb = 2048
    elif host_mem_mb >= 8192.0:
        base_floor_mb = 1024
    else:
        base_floor_mb = 512

    adjusted_base_mem_mb = max(int(base_mem_mb), base_floor_mb)
    if adjusted_base_mem_mb != int(base_mem_mb):
        notes.append(f"base_mem_mb raised to {adjusted_base_mem_mb} based on host memory tier")

    avg_runtime_factor = 1.3
    safe_budget_mb = host_mem_mb * 0.90
    max_tasks_by_budget = int(safe_budget_mb / max(1.0, float(adjusted_base_mem_mb) * avg_runtime_factor))
    if max_tasks_by_budget >= min_task_count and adjusted_task_count > max_tasks_by_budget:
        adjusted_task_count = max_tasks_by_budget
        notes.append(f"task_count reduced to {adjusted_task_count} to keep no-scheduler stage within safe budget")
    elif max_tasks_by_budget < min_task_count:
        base_by_budget = int(safe_budget_mb / max(1.0, float(min_task_count) * avg_runtime_factor))
        lowered_base = max(256, base_by_budget)
        if lowered_base < adjusted_base_mem_mb:
            notes.append(
                f"base_mem_mb reduced to {lowered_base} due host budget, while preserving minimum task_count={min_task_count}"
            )
            adjusted_base_mem_mb = lowered_base

    predicted_no_scheduler_load_pct = round(
        100.0 * (float(adjusted_task_count) * float(adjusted_base_mem_mb) * avg_runtime_factor) / max(1.0, host_mem_mb),
        4,
    )
    predicted_fixed_worker_load_pct = round(
        100.0 * (float(workers) * float(adjusted_base_mem_mb) * avg_runtime_factor) / max(1.0, host_mem_mb),
        4,
    )

    return {
        "task_count": int(adjusted_task_count),
        "duration_sec": float(adjusted_duration_sec),
        "base_mem_mb": int(adjusted_base_mem_mb),
        "fixed_workers": int(workers),
        "host_total_mem_mb": round(host_mem_mb, 3),
        "predicted_no_scheduler_load_pct": predicted_no_scheduler_load_pct,
        "predicted_fixed_worker_load_pct": predicted_fixed_worker_load_pct,
        "notes": notes,
    }


def plan_eventful_scheduler_thresholds(attempt_index: int) -> Dict[str, float]:
    idx = max(0, int(attempt_index))
    memory_high_pct = max(60.0, 76.0 - 5.0 * float(idx))
    memory_emergency_pct = min(100.0, max(memory_high_pct + 4.0, 82.0 - 6.0 * float(idx)))
    if memory_high_pct >= memory_emergency_pct:
        memory_high_pct = max(1.0, memory_emergency_pct - 1.0)
    preempt_count = float(max(1, 1 + (idx // 2)))
    return {
        "memory_high_pct": round(memory_high_pct, 3),
        "memory_emergency_pct": round(memory_emergency_pct, 3),
        "cpu_high_pct": 99.9,
        "cpu_hard_pct": 100.0,
        "preempt_count_per_tick": preempt_count,
    }


def apply_eventful_threshold_bias(base_cfg: Dict[str, float], threshold_bias: float) -> Dict[str, float]:
    high = max(50.0, min(98.0, float(base_cfg["memory_high_pct"]) + float(threshold_bias)))
    emergency = max(high + 1.0, min(99.0, float(base_cfg["memory_emergency_pct"]) + float(threshold_bias)))
    return {
        "memory_high_pct": round(high, 3),
        "memory_emergency_pct": round(emergency, 3),
        "cpu_high_pct": float(base_cfg["cpu_high_pct"]),
        "cpu_hard_pct": float(base_cfg["cpu_hard_pct"]),
        "preempt_count_per_tick": float(max(1.0, float(base_cfg["preempt_count_per_tick"]))),
    }


def update_eventful_threshold_bias(current_bias: float, retry_reason: str) -> float:
    if retry_reason == "insufficient_completion":
        return min(20.0, float(current_bias) + 8.0)
    if retry_reason in {"low_signal_dynamic", "missing_emergency_signal", "missing_dynamic_row"}:
        return max(-20.0, float(current_bias) - 4.0)
    return float(current_bias)


def _generate_real_workload(task_count: int, duration_sec: float, base_mem_mb: int, seed: int) -> List[TaskSpec]:
    rng = random.Random(seed)
    tasks: List[TaskSpec] = []
    for i in range(task_count):
        bucket = rng.random()
        if bucket < 0.34:
            mem_mb = int(base_mem_mb * 1.8)
            loop_scale = 4500
            est_cpu = 0.0
        elif bucket < 0.67:
            mem_mb = int(base_mem_mb * 0.8)
            loop_scale = 14000
            est_cpu = 0.0
        else:
            mem_mb = int(base_mem_mb * 1.2)
            loop_scale = 9000
            est_cpu = 0.0
        task = TaskSpec(
            task_id=f"REAL-T-{i:03d}",
            command=_worker_command(mem_mb, duration_sec, loop_scale),
            priority=(i % 6) + 1,
            estimated_mem_mb=max(64, int(mem_mb * 1.15)),
            estimated_cpu_percent=est_cpu,
            estimated_gpu_mem_mb=0,
            preemptible=True,
            max_runtime_sec=max(8.0, duration_sec * 2.5),
        )
        tasks.append(task)
    return tasks


def _wait_all(processes: List[subprocess.Popen]) -> Tuple[int, int]:
    completed = 0
    nonzero = 0
    for p in processes:
        rc = p.wait()
        completed += 1
        if rc != 0:
            nonzero += 1
    return completed, nonzero


def run_real_machine_baseline(
    *,
    task_count: int = 18,
    duration_sec: float = 2.0,
    base_mem_mb: int = 64,
    fixed_workers: int = 4,
    seed: int = 20260211,
    max_scheduler_wall_sec: float = 120.0,
    dynamic_memory_high_pct: float = 85.0,
    dynamic_memory_emergency_pct: float = 92.0,
    dynamic_preempt_count_per_tick: int = 1,
    dynamic_cpu_high_pct: float = 99.9,
    dynamic_cpu_hard_pct: float = 100.0,
) -> Dict[str, object]:
    planned = plan_real_baseline_params(
        task_count=task_count,
        duration_sec=duration_sec,
        base_mem_mb=base_mem_mb,
        fixed_workers=fixed_workers,
    )
    task_count_eff = int(planned["task_count"])
    duration_sec_eff = float(planned["duration_sec"])
    base_mem_mb_eff = int(planned["base_mem_mb"])
    fixed_workers_eff = int(planned["fixed_workers"])
    tasks = _generate_real_workload(task_count_eff, duration_sec_eff, base_mem_mb_eff, seed)

    results: List[Dict[str, object]] = []

    # A) No scheduler: start all tasks immediately.
    start = time.time()
    with PeakSampler() as sampler:
        procs = [subprocess.Popen(t.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for t in tasks]
        completed, nonzero = _wait_all(procs)
    wall = time.time() - start
    results.append(
        {
            "mode": "A_no_scheduler",
            "submitted": task_count_eff,
            "completed": completed,
            "nonzero_exit_count": nonzero,
            "completion_rate": round(completed / max(1, task_count_eff), 4),
            "wall_time_sec": round(wall, 4),
            "throughput_tps": round(completed / max(0.001, wall), 4),
            "peak_memory_pct": _round_opt(sampler.peak_memory_pct),
            "peak_swap_pct": _round_opt(sampler.peak_swap_pct),
            "peak_gpu_memory_pct": _round_opt(sampler.peak_gpu_memory_pct),
        }
    )

    # B) Fixed concurrency baseline.
    start = time.time()
    with PeakSampler() as sampler:
        pending = list(tasks)
        running: List[subprocess.Popen] = []
        completed = 0
        nonzero = 0
        while pending or running:
            while pending and len(running) < fixed_workers_eff:
                task = pending.pop(0)
                running.append(
                    subprocess.Popen(task.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                )
            still_running: List[subprocess.Popen] = []
            for p in running:
                rc = p.poll()
                if rc is None:
                    still_running.append(p)
                else:
                    completed += 1
                    if rc != 0:
                        nonzero += 1
            running = still_running
            time.sleep(0.05)
    wall = time.time() - start
    results.append(
        {
            "mode": "B_fixed_concurrency",
            "submitted": task_count_eff,
            "completed": completed,
            "nonzero_exit_count": nonzero,
            "completion_rate": round(completed / max(1, task_count_eff), 4),
            "wall_time_sec": round(wall, 4),
            "throughput_tps": round(completed / max(0.001, wall), 4),
            "peak_memory_pct": _round_opt(sampler.peak_memory_pct),
            "peak_swap_pct": _round_opt(sampler.peak_swap_pct),
            "peak_gpu_memory_pct": _round_opt(sampler.peak_gpu_memory_pct),
        }
    )

    # C) Dynamic scheduler.
    cfg = SchedulerConfig(
        dry_run=False,
        max_workers=fixed_workers_eff,
        min_workers=1,
        check_interval_sec=0.1,
        reserve_memory_mb=512,
        memory_high_pct=float(dynamic_memory_high_pct),
        memory_emergency_pct=float(dynamic_memory_emergency_pct),
        cpu_high_pct=float(dynamic_cpu_high_pct),
        cpu_hard_pct=float(dynamic_cpu_hard_pct),
        preempt_count_per_tick=int(max(1, dynamic_preempt_count_per_tick)),
    )
    exp_monitor = CpuCappedMonitor(cpu_cap_pct=99.0, enable_gpu=cfg.enable_gpu_guard)
    scheduler = DynamicTaskScheduler(cfg, monitor=exp_monitor)
    for task in tasks:
        scheduler.submit_task(task)

    start = time.time()
    scheduler_timeout_hit = False
    stalled_no_admission = False
    stagnant_ticks = 0
    no_progress_limit = max(10, int(10.0 / max(0.01, cfg.check_interval_sec)))
    max_wall = max(5.0, float(max_scheduler_wall_sec))
    deadline = start + max_wall
    prev_pending = len(scheduler.pending)
    prev_running = len(scheduler.running)
    with PeakSampler() as sampler:
        while scheduler.pending or scheduler.running:
            scheduler.tick()
            curr_pending = len(scheduler.pending)
            curr_running = len(scheduler.running)
            if curr_pending == prev_pending and curr_running == prev_running and curr_running == 0 and curr_pending > 0:
                stagnant_ticks += 1
            else:
                stagnant_ticks = 0
            prev_pending = curr_pending
            prev_running = curr_running
            if time.time() >= deadline:
                scheduler_timeout_hit = True
                break
            if stagnant_ticks >= no_progress_limit:
                stalled_no_admission = True
                break
            time.sleep(cfg.check_interval_sec)
        scheduler.shutdown()
    wall = time.time() - start
    m = scheduler.metrics_dict()
    completed = int(m["completed_total"])
    nonzero = int(m["failed_total"] + m["timeout_total"])
    unfinished = int(len(scheduler.pending) + len(scheduler.running))
    started_total = int(m["started_total"])
    emergency_signal_missing = (
        int(m["emergency_ticks"]) == 0 and int(m["preempted_total"]) == 0
    )
    low_signal_dynamic = (
        started_total == 0
        or (
            int(m["blocked_total"]) == 0
            and int(m["preempted_total"]) == 0
            and int(m["emergency_ticks"]) == 0
        )
    )
    results.append(
        {
            "mode": "C_dynamic_scheduler",
            "submitted": task_count_eff,
            "completed": completed,
            "started_total": started_total,
            "nonzero_exit_count": nonzero,
            "completion_rate": round(completed / max(1, task_count_eff), 4),
            "wall_time_sec": round(wall, 4),
            "throughput_tps": round(completed / max(0.001, wall), 4),
            "peak_memory_pct": _round_opt(sampler.peak_memory_pct),
            "peak_swap_pct": _round_opt(sampler.peak_swap_pct),
            "peak_gpu_memory_pct": _round_opt(sampler.peak_gpu_memory_pct),
            "blocked_event_total": int(m["blocked_total"]),
            "preempted_total": int(m["preempted_total"]),
            "emergency_ticks": int(m["emergency_ticks"]),
            "unfinished_tasks": unfinished,
            "scheduler_timeout_hit": int(1 if scheduler_timeout_hit else 0),
            "stalled_no_admission": int(1 if stalled_no_admission else 0),
            "low_signal_dynamic": int(1 if low_signal_dynamic else 0),
            "emergency_signal_missing": int(1 if emergency_signal_missing else 0),
            "cpu_clip_events": int(exp_monitor.clipped_samples),
        }
    )

    return {
        "evidence_id": "REAL-BASELINE",
        "task_count": task_count_eff,
        "task_duration_sec": duration_sec_eff,
        "base_mem_mb": base_mem_mb_eff,
        "fixed_workers": fixed_workers_eff,
        "seed": seed,
        "max_scheduler_wall_sec": max_wall,
        "planning_notes": planned["notes"],
        "host_total_mem_mb": planned["host_total_mem_mb"],
        "predicted_no_scheduler_load_pct": planned["predicted_no_scheduler_load_pct"],
        "predicted_fixed_worker_load_pct": planned["predicted_fixed_worker_load_pct"],
        "dynamic_memory_high_pct": float(dynamic_memory_high_pct),
        "dynamic_memory_emergency_pct": float(dynamic_memory_emergency_pct),
        "dynamic_cpu_high_pct": float(dynamic_cpu_high_pct),
        "dynamic_cpu_hard_pct": float(dynamic_cpu_hard_pct),
        "dynamic_preempt_count_per_tick": int(max(1, dynamic_preempt_count_per_tick)),
        "psutil_available": int(psutil is not None),
        "nvidia_smi_available": int(1 if shutil.which("nvidia-smi") is not None else 0),
        "results": results,
    }


def _find_dynamic_row(result: Dict[str, object]) -> Optional[Dict[str, object]]:
    rows = result.get("results")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("mode")) == "C_dynamic_scheduler":
            return row
    return None


def need_eventful_retry(
    dynamic_row: Dict[str, object],
    *,
    require_completion: bool = False,
    min_completed: int = 1,
) -> Tuple[bool, str]:
    low_signal = int(dynamic_row.get("low_signal_dynamic", 0))
    emergency_missing = int(dynamic_row.get("emergency_signal_missing", 0))
    if low_signal == 1:
        return True, "low_signal_dynamic"
    if emergency_missing == 1:
        return True, "missing_emergency_signal"
    if require_completion and int(dynamic_row.get("completed", 0)) < max(0, int(min_completed)):
        return True, "insufficient_completion"
    return False, "satisfied"


def escalate_real_baseline_params(
    *,
    task_count: int,
    duration_sec: float,
    base_mem_mb: int,
    fixed_workers: int,
    host_total_mem_mb: Optional[float] = None,
) -> Dict[str, object]:
    workers = max(1, int(fixed_workers))
    next_task_count = int(task_count) + max(2, workers // 2)
    next_duration_sec = min(20.0, max(6.0, float(duration_sec)) + 2.0)
    next_base_mem_mb = max(256, int(round(float(base_mem_mb) * 1.25)))
    planned = plan_real_baseline_params(
        task_count=next_task_count,
        duration_sec=next_duration_sec,
        base_mem_mb=next_base_mem_mb,
        fixed_workers=workers,
        host_total_mem_mb=host_total_mem_mb,
    )
    notes = list(planned.get("notes", []))
    notes.append("escalated for eventful retry")
    planned["notes"] = notes
    return planned


def run_real_machine_baseline_until_eventful(
    *,
    max_attempts: int = 3,
    task_count: int = 18,
    duration_sec: float = 2.0,
    base_mem_mb: int = 64,
    fixed_workers: int = 4,
    seed: int = 20260211,
    seed_step: int = 37,
    max_scheduler_wall_sec: float = 120.0,
    require_completion: bool = False,
    min_completed: int = 1,
) -> Dict[str, object]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if seed_step < 1:
        raise ValueError("seed_step must be >= 1")

    current = plan_real_baseline_params(
        task_count=task_count,
        duration_sec=duration_sec,
        base_mem_mb=base_mem_mb,
        fixed_workers=fixed_workers,
    )

    attempts: List[Dict[str, object]] = []
    final_result: Optional[Dict[str, object]] = None
    eventful_achieved = 0
    dynamic_wall = max(5.0, float(max_scheduler_wall_sec))
    threshold_bias = 0.0
    for idx in range(max_attempts):
        dynamic_cfg = apply_eventful_threshold_bias(plan_eventful_scheduler_thresholds(idx), threshold_bias)
        run_seed = int(seed + idx * seed_step)
        result = run_real_machine_baseline(
            task_count=int(current["task_count"]),
            duration_sec=float(current["duration_sec"]),
            base_mem_mb=int(current["base_mem_mb"]),
            fixed_workers=int(current["fixed_workers"]),
            seed=run_seed,
            max_scheduler_wall_sec=dynamic_wall,
            dynamic_memory_high_pct=float(dynamic_cfg["memory_high_pct"]),
            dynamic_memory_emergency_pct=float(dynamic_cfg["memory_emergency_pct"]),
            dynamic_preempt_count_per_tick=int(dynamic_cfg["preempt_count_per_tick"]),
            dynamic_cpu_high_pct=float(dynamic_cfg["cpu_high_pct"]),
            dynamic_cpu_hard_pct=float(dynamic_cfg["cpu_hard_pct"]),
        )
        dynamic_row = _find_dynamic_row(result) or {}
        if dynamic_row:
            retry_needed, retry_reason = need_eventful_retry(
                dynamic_row,
                require_completion=require_completion,
                min_completed=min_completed,
            )
        else:
            retry_needed, retry_reason = (True, "missing_dynamic_row")
        adaptation_action = "stop"
        if retry_needed:
            adaptation_action = (
                "relax_and_hold" if retry_reason == "insufficient_completion" else "tighten_and_escalate"
            )
        attempts.append(
            {
                "attempt": idx + 1,
                "seed": run_seed,
                "threshold_bias": round(float(threshold_bias), 3),
                "adaptation_action": adaptation_action,
                "params": {
                    "task_count": int(current["task_count"]),
                    "duration_sec": float(current["duration_sec"]),
                    "base_mem_mb": int(current["base_mem_mb"]),
                    "fixed_workers": int(current["fixed_workers"]),
                    "dynamic_memory_high_pct": float(dynamic_cfg["memory_high_pct"]),
                    "dynamic_memory_emergency_pct": float(dynamic_cfg["memory_emergency_pct"]),
                    "dynamic_preempt_count_per_tick": int(dynamic_cfg["preempt_count_per_tick"]),
                    "max_scheduler_wall_sec": float(dynamic_wall),
                },
                "dynamic_summary": {
                    "started_total": int(dynamic_row.get("started_total", 0)),
                    "completed": int(dynamic_row.get("completed", 0)),
                    "blocked_event_total": int(dynamic_row.get("blocked_event_total", 0)),
                    "preempted_total": int(dynamic_row.get("preempted_total", 0)),
                    "emergency_ticks": int(dynamic_row.get("emergency_ticks", 0)),
                    "low_signal_dynamic": int(dynamic_row.get("low_signal_dynamic", 1)),
                    "emergency_signal_missing": int(dynamic_row.get("emergency_signal_missing", 1)),
                    "scheduler_timeout_hit": int(dynamic_row.get("scheduler_timeout_hit", 0)),
                },
                "retry_needed": int(1 if retry_needed else 0),
                "retry_reason": retry_reason,
            }
        )
        final_result = result
        if not retry_needed:
            eventful_achieved = 1
            break
        if idx + 1 < max_attempts:
            if retry_reason == "insufficient_completion":
                dynamic_wall = min(120.0, dynamic_wall + 8.0)
            else:
                current = escalate_real_baseline_params(
                    task_count=int(current["task_count"]),
                    duration_sec=float(current["duration_sec"]),
                    base_mem_mb=int(current["base_mem_mb"]),
                    fixed_workers=int(current["fixed_workers"]),
                    host_total_mem_mb=float(result.get("host_total_mem_mb", current["host_total_mem_mb"])),
                )
            threshold_bias = update_eventful_threshold_bias(threshold_bias, retry_reason)

    if final_result is None:
        raise RuntimeError("Unexpected empty eventful baseline run")

    return {
        "evidence_id": "REAL-BASELINE-EVENTFUL",
        "max_attempts": int(max_attempts),
        "attempts_executed": len(attempts),
        "eventful_achieved": int(eventful_achieved),
        "require_completion": int(1 if require_completion else 0),
        "min_completed": int(max(0, min_completed)),
        "seed": int(seed),
        "seed_step": int(seed_step),
        "attempts": attempts,
        "final_result": final_result,
    }


def summarize_real_baseline_runs(runs: Sequence[Dict[str, object]]) -> Dict[str, object]:
    if not runs:
        raise ValueError("runs must be non-empty")
    mode_to_rows: Dict[str, List[Dict[str, object]]] = {}
    for run in runs:
        for row in run["results"]:  # type: ignore[index]
            mode = str(row["mode"])  # type: ignore[index]
            mode_to_rows.setdefault(mode, []).append(row)

    metric_names = [
        "completion_rate",
        "wall_time_sec",
        "throughput_tps",
        "started_total",
        "nonzero_exit_count",
        "peak_memory_pct",
        "peak_swap_pct",
        "peak_gpu_memory_pct",
        "blocked_event_total",
        "preempted_total",
        "emergency_ticks",
        "unfinished_tasks",
        "scheduler_timeout_hit",
        "stalled_no_admission",
        "low_signal_dynamic",
        "emergency_signal_missing",
        "cpu_clip_events",
    ]
    by_mode: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    for mode, rows in mode_to_rows.items():
        mode_stats: Dict[str, Dict[str, Optional[float]]] = {}
        for metric in metric_names:
            values: List[Optional[float]] = []
            for row in rows:
                value = row.get(metric) if isinstance(row, dict) else None
                if value is None:
                    values.append(None)
                else:
                    values.append(float(value))
            mode_stats[metric] = _mean_ci95_optional(values)
        by_mode[mode] = mode_stats

    return {
        "repeat_runs": len(runs),
        "by_mode": by_mode,
    }


def run_real_machine_multirun_confidence_summary(
    *,
    repeat_runs: int = 3,
    task_count: int = 18,
    duration_sec: float = 2.0,
    base_mem_mb: int = 64,
    fixed_workers: int = 4,
    base_seed: int = 20260211,
    seed_step: int = 101,
    cooldown_sec: float = 0.0,
    max_scheduler_wall_sec: float = 120.0,
) -> Dict[str, object]:
    if repeat_runs < 2:
        raise ValueError("repeat_runs must be >= 2")
    if seed_step < 1:
        raise ValueError("seed_step must be >= 1")
    if cooldown_sec < 0:
        raise ValueError("cooldown_sec must be >= 0")

    run_records: List[Dict[str, object]] = []
    seed_list: List[int] = []
    for idx in range(repeat_runs):
        seed = int(base_seed + idx * seed_step)
        seed_list.append(seed)
        result = run_real_machine_baseline(
            task_count=task_count,
            duration_sec=duration_sec,
            base_mem_mb=base_mem_mb,
            fixed_workers=fixed_workers,
            seed=seed,
            max_scheduler_wall_sec=max_scheduler_wall_sec,
        )
        run_records.append(
            {
                "run_index": idx,
                "seed": seed,
                "result": result,
            }
        )
        if idx + 1 < repeat_runs and cooldown_sec > 0:
            time.sleep(cooldown_sec)

    summary = summarize_real_baseline_runs([record["result"] for record in run_records])  # type: ignore[index]
    return {
        "evidence_id": "REAL-BASELINE-MULTI",
        "repeat_runs": repeat_runs,
        "task_count": task_count,
        "task_duration_sec": duration_sec,
        "base_mem_mb": base_mem_mb,
        "fixed_workers": fixed_workers,
        "base_seed": base_seed,
        "seed_step": seed_step,
        "cooldown_sec": cooldown_sec,
        "max_scheduler_wall_sec": max_scheduler_wall_sec,
        "seed_list": seed_list,
        "runs": run_records,
        "summary": summary,
    }


def _flatten_rows(payload: Dict[str, object]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    p04 = payload["p04"]  # type: ignore[index]
    p05 = payload["p05"]  # type: ignore[index]

    rows.append(
        {
            "evidence_id": "P-04",
            "scenario": p04["scenario"],  # type: ignore[index]
            "trials": p04["trials"],  # type: ignore[index]
            "per_gpu_false_block_rate": p04["per_gpu_false_block_rate"],  # type: ignore[index]
            "aggregate_false_block_rate": p04["aggregate_false_block_rate"],  # type: ignore[index]
            "false_block_reduction": p04["false_block_reduction"],  # type: ignore[index]
        }
    )
    for scenario_name, stats in p04["scenario_breakdown"].items():  # type: ignore[index]
        rows.append(
            {
                "evidence_id": "P-04-SCENARIO",
                "scenario": scenario_name,
                "trials": stats["trials"],
                "safe_cases": stats["safe_cases"],
                "per_gpu_false_block_rate": stats["per_gpu_false_block_rate"],
                "aggregate_false_block_rate": stats["aggregate_false_block_rate"],
                "false_block_reduction": stats["false_block_reduction"],
            }
        )
    rows.append(
        {
            "evidence_id": "P-05",
            "scenario": p05["scenario"],  # type: ignore[index]
            "trials": p05["trials"],  # type: ignore[index]
            "avg_preemptions_normalized": p05["avg_preemptions_normalized"],  # type: ignore[index]
            "avg_preemptions_raw_mb": p05["avg_preemptions_raw_mb"],  # type: ignore[index]
            "avg_preemptions_random": p05["avg_preemptions_random"],  # type: ignore[index]
            "recovery_rate_normalized": p05["recovery_rate_normalized"],  # type: ignore[index]
            "recovery_rate_raw_mb": p05["recovery_rate_raw_mb"],  # type: ignore[index]
            "recovery_rate_random": p05["recovery_rate_random"],  # type: ignore[index]
        }
    )
    rows.append(
        {
            "evidence_id": "P-05-TIGHT",
            "scenario": p05["scenario"],  # type: ignore[index]
            "trials": p05["trials"],  # type: ignore[index]
            "tight_preempt_limit": p05["tight_preempt_limit"],  # type: ignore[index]
            "avg_preemptions_normalized": p05["avg_preemptions_normalized_tight"],  # type: ignore[index]
            "avg_preemptions_raw_mb": p05["avg_preemptions_raw_mb_tight"],  # type: ignore[index]
            "avg_preemptions_random": p05["avg_preemptions_random_tight"],  # type: ignore[index]
            "recovery_rate_normalized": p05["recovery_rate_normalized_tight"],  # type: ignore[index]
            "recovery_rate_raw_mb": p05["recovery_rate_raw_mb_tight"],  # type: ignore[index]
            "recovery_rate_random": p05["recovery_rate_random_tight"],  # type: ignore[index]
        }
    )

    if "real_baseline" in payload:
        real = payload["real_baseline"]  # type: ignore[index]
        for item in real["results"]:  # type: ignore[index]
            row = {"evidence_id": "REAL-BASELINE"}
            row.update(item)
            rows.append(row)

    if "real_baseline_eventful" in payload:
        eventful = payload["real_baseline_eventful"]  # type: ignore[index]
        for att in eventful["attempts"]:  # type: ignore[index]
            dyn = att["dynamic_summary"]  # type: ignore[index]
            row = {
                "evidence_id": "REAL-BASELINE-ATTEMPT",
                "attempt": att["attempt"],  # type: ignore[index]
                "seed": att["seed"],  # type: ignore[index]
                "task_count": att["params"]["task_count"],  # type: ignore[index]
                "task_duration_sec": att["params"]["duration_sec"],  # type: ignore[index]
                "base_mem_mb": att["params"]["base_mem_mb"],  # type: ignore[index]
                "fixed_workers": att["params"]["fixed_workers"],  # type: ignore[index]
                "dynamic_memory_high_pct": att["params"]["dynamic_memory_high_pct"],  # type: ignore[index]
                "dynamic_memory_emergency_pct": att["params"]["dynamic_memory_emergency_pct"],  # type: ignore[index]
                "dynamic_preempt_count_per_tick": att["params"]["dynamic_preempt_count_per_tick"],  # type: ignore[index]
                "max_scheduler_wall_sec": att["params"]["max_scheduler_wall_sec"],  # type: ignore[index]
                "threshold_bias": att.get("threshold_bias", 0.0),
                "adaptation_action": att.get("adaptation_action", ""),
                "started_total": dyn["started_total"],
                "completed": dyn["completed"],
                "blocked_event_total": dyn["blocked_event_total"],
                "preempted_total": dyn["preempted_total"],
                "emergency_ticks": dyn["emergency_ticks"],
                "low_signal_dynamic": dyn["low_signal_dynamic"],
                "emergency_signal_missing": dyn["emergency_signal_missing"],
                "scheduler_timeout_hit": dyn["scheduler_timeout_hit"],
                "retry_needed": att["retry_needed"],  # type: ignore[index]
                "retry_reason": att["retry_reason"],  # type: ignore[index]
            }
            rows.append(row)

    if "real_baseline_multirun" in payload:
        real_multi = payload["real_baseline_multirun"]  # type: ignore[index]
        for run in real_multi["runs"]:  # type: ignore[index]
            run_idx = run["run_index"]  # type: ignore[index]
            run_seed = run["seed"]  # type: ignore[index]
            result = run["result"]  # type: ignore[index]
            for item in result["results"]:  # type: ignore[index]
                row = {
                    "evidence_id": "REAL-BASELINE-RUN",
                    "run_index": run_idx,
                    "seed": run_seed,
                }
                row.update(item)
                rows.append(row)
        summary = real_multi["summary"]  # type: ignore[index]
        for mode, mode_metrics in summary["by_mode"].items():  # type: ignore[index]
            for metric_name, metric_stats in mode_metrics.items():
                rows.append(
                    {
                        "evidence_id": "REAL-BASELINE-CI",
                        "mode": mode,
                        "metric": metric_name,
                        "repeat_runs": real_multi["repeat_runs"],  # type: ignore[index]
                        "mean": metric_stats["mean"],
                        "stddev": metric_stats["stddev"],
                        "ci95_low": metric_stats["ci95_low"],
                        "ci95_high": metric_stats["ci95_high"],
                        "min": metric_stats["min"],
                        "max": metric_stats["max"],
                        "n": metric_stats["n"],
                    }
                )

    if "multiseed" in payload:
        multiseed = payload["multiseed"]  # type: ignore[index]
        for metric_name, summary in multiseed["metrics"].items():  # type: ignore[index]
            rows.append(
                {
                    "evidence_id": "MULTI-SEED-CI",
                    "metric": metric_name,
                    "seed_runs": multiseed["seed_runs"],  # type: ignore[index]
                    "trials_per_seed": multiseed["trials_per_seed"],  # type: ignore[index]
                    "mean": summary["mean"],
                    "stddev": summary["stddev"],
                    "ci95_low": summary["ci95_low"],
                    "ci95_high": summary["ci95_high"],
                    "min": summary["min"],
                    "max": summary["max"],
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Advanced research experiments for resource scheduler.")
    parser.add_argument("--trials", type=int, default=4000, help="Trial count for P-04 and P-05 ablations.")
    parser.add_argument("--seed", type=int, default=20260211)
    parser.add_argument(
        "--p05-tight-preempt-limit",
        type=int,
        default=5,
        help="Tight preempt limit used by the P-05 stress variant.",
    )
    parser.add_argument("--run-real-baseline", action="store_true", help="Run real process baseline experiment.")
    parser.add_argument("--real-task-count", type=int, default=18)
    parser.add_argument("--real-task-duration-sec", type=float, default=2.0)
    parser.add_argument("--real-base-mem-mb", type=int, default=64)
    parser.add_argument("--real-fixed-workers", type=int, default=4)
    parser.add_argument(
        "--real-repeat-runs",
        type=int,
        default=1,
        help="If >=2, run repeated real baseline and emit CI summary.",
    )
    parser.add_argument(
        "--real-seed-step",
        type=int,
        default=101,
        help="Seed increment between repeated real baseline runs.",
    )
    parser.add_argument(
        "--real-cooldown-sec",
        type=float,
        default=0.0,
        help="Cooldown sleep between repeated real baseline runs.",
    )
    parser.add_argument(
        "--real-max-wall-sec",
        type=float,
        default=120.0,
        help="Max wall time for dynamic scheduler stage in each real baseline run.",
    )
    parser.add_argument(
        "--real-target-eventful",
        action="store_true",
        help="Single-run mode: auto-retry real baseline until eventful dynamic evidence is observed.",
    )
    parser.add_argument(
        "--real-max-attempts",
        type=int,
        default=3,
        help="Max attempts for --real-target-eventful mode.",
    )
    parser.add_argument(
        "--real-attempt-seed-step",
        type=int,
        default=37,
        help="Seed increment between attempts for --real-target-eventful mode.",
    )
    parser.add_argument(
        "--real-require-completion",
        action="store_true",
        help="Eventful mode additionally requires dynamic completed >= --real-min-completed.",
    )
    parser.add_argument(
        "--real-min-completed",
        type=int,
        default=1,
        help="Minimum completed tasks required when --real-require-completion is enabled.",
    )
    parser.add_argument(
        "--multi-seed-runs",
        type=int,
        default=0,
        help="If >=2, run repeated P-04/P-05 experiments and output CI summary.",
    )
    parser.add_argument(
        "--multi-seed-trials",
        type=int,
        default=0,
        help="Trials per seed for multi-seed mode. 0 means reuse --trials.",
    )
    parser.add_argument(
        "--multi-seed-step",
        type=int,
        default=9973,
        help="Seed increment between runs in multi-seed mode.",
    )
    args = parser.parse_args()

    p04 = run_p04_per_gpu_affinity_ablation(trials=args.trials, seed=args.seed)
    p05 = run_p05_preemption_ablation(
        trials=args.trials,
        seed=args.seed,
        tight_preempt_limit=args.p05_tight_preempt_limit,
    )

    payload: Dict[str, object] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "p04": p04,
        "p05": p05,
    }
    if args.run_real_baseline:
        if args.real_repeat_runs >= 2:
            payload["real_baseline_multirun"] = run_real_machine_multirun_confidence_summary(
                repeat_runs=args.real_repeat_runs,
                task_count=args.real_task_count,
                duration_sec=args.real_task_duration_sec,
                base_mem_mb=args.real_base_mem_mb,
                fixed_workers=args.real_fixed_workers,
                base_seed=args.seed,
                seed_step=args.real_seed_step,
                cooldown_sec=args.real_cooldown_sec,
                max_scheduler_wall_sec=args.real_max_wall_sec,
            )
            first_run = payload["real_baseline_multirun"]["runs"][0]["result"]  # type: ignore[index]
            payload["real_baseline"] = first_run
        elif args.real_target_eventful:
            payload["real_baseline_eventful"] = run_real_machine_baseline_until_eventful(
                max_attempts=args.real_max_attempts,
                task_count=args.real_task_count,
                duration_sec=args.real_task_duration_sec,
                base_mem_mb=args.real_base_mem_mb,
                fixed_workers=args.real_fixed_workers,
                seed=args.seed,
                seed_step=args.real_attempt_seed_step,
                max_scheduler_wall_sec=args.real_max_wall_sec,
                require_completion=args.real_require_completion,
                min_completed=args.real_min_completed,
            )
            payload["real_baseline"] = payload["real_baseline_eventful"]["final_result"]  # type: ignore[index]
        else:
            payload["real_baseline"] = run_real_machine_baseline(
                task_count=args.real_task_count,
                duration_sec=args.real_task_duration_sec,
                base_mem_mb=args.real_base_mem_mb,
                fixed_workers=args.real_fixed_workers,
                seed=args.seed,
                max_scheduler_wall_sec=args.real_max_wall_sec,
            )
    if args.multi_seed_runs >= 2:
        multi_trials = args.multi_seed_trials if args.multi_seed_trials > 0 else args.trials
        payload["multiseed"] = run_multiseed_confidence_summary(
            trials_per_seed=multi_trials,
            seed_runs=args.multi_seed_runs,
            base_seed=args.seed,
            seed_step=args.multi_seed_step,
            tight_preempt_limit=args.p05_tight_preempt_limit,
        )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    rows = _flatten_rows(payload)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[OK] wrote: {CSV_PATH}")
    print(f"[OK] wrote: {JSON_PATH}")


if __name__ == "__main__":
    main()
