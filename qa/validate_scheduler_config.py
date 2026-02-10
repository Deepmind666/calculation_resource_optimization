#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "spec" / "scheduler_config.example.json"


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def _resolve_config_path(argv: list[str]) -> Path:
    if len(argv) > 2:
        fail("Usage: validate_scheduler_config.py [config_path]")
    if len(argv) == 2:
        return Path(argv[1]).resolve()
    return CONFIG


def main() -> None:
    config_path = _resolve_config_path(sys.argv)
    if not config_path.exists():
        fail(f"Missing config: {config_path}")

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    required_keys = {
        "max_workers",
        "min_workers",
        "check_interval_sec",
        "memory_high_pct",
        "memory_emergency_pct",
        "cpu_high_pct",
        "cpu_hard_pct",
        "swap_emergency_pct",
        "enable_gpu_guard",
        "gpu_memory_high_pct",
        "gpu_memory_emergency_pct",
        "reserve_memory_mb",
        "high_mode_priority_cutoff",
        "preempt_count_per_tick",
        "kill_timeout_sec",
        "mode_hysteresis_pct",
        "emergency_cooldown_ticks",
        "ema_alpha",
        "max_start_per_tick_normal",
        "max_start_per_tick_high",
        "max_event_log_entries",
        "dry_run",
    }
    missing = sorted(required_keys - set(cfg.keys()))
    if missing:
        fail(f"Missing keys: {missing}")
    unknown = sorted(set(cfg.keys()) - required_keys)
    if unknown:
        fail(f"Unknown keys: {unknown}")

    if not (cfg["min_workers"] >= 1 and cfg["max_workers"] >= cfg["min_workers"]):
        fail("Invalid worker range.")
    if float(cfg["check_interval_sec"]) <= 0:
        fail("check_interval_sec must be > 0.")
    if int(cfg["max_start_per_tick_normal"]) < 1 or int(cfg["max_start_per_tick_high"]) < 1:
        fail("max_start_per_tick_* must be >= 1.")
    if int(cfg["preempt_count_per_tick"]) < 1:
        fail("preempt_count_per_tick must be >= 1.")
    if int(cfg["high_mode_priority_cutoff"]) < 1:
        fail("high_mode_priority_cutoff must be >= 1.")
    if int(cfg["reserve_memory_mb"]) < 0:
        fail("reserve_memory_mb must be >= 0.")
    if float(cfg["kill_timeout_sec"]) <= 0:
        fail("kill_timeout_sec must be > 0.")
    if int(cfg["max_event_log_entries"]) < 1:
        fail("max_event_log_entries must be >= 1.")
    if int(cfg["emergency_cooldown_ticks"]) < 0:
        fail("emergency_cooldown_ticks must be >= 0.")
    if float(cfg["mode_hysteresis_pct"]) < 0:
        fail("mode_hysteresis_pct must be >= 0.")
    if not (0.0 <= float(cfg["ema_alpha"]) <= 1.0):
        fail("ema_alpha must be in [0, 1].")

    for k in [
        "memory_high_pct",
        "memory_emergency_pct",
        "cpu_high_pct",
        "cpu_hard_pct",
        "swap_emergency_pct",
        "gpu_memory_high_pct",
        "gpu_memory_emergency_pct",
    ]:
        v = float(cfg[k])
        if not (0.0 < v <= 100.0):
            fail(f"{k} must be in (0, 100].")

    if float(cfg["memory_high_pct"]) >= float(cfg["memory_emergency_pct"]):
        fail("memory_high_pct must be < memory_emergency_pct.")
    if float(cfg["cpu_high_pct"]) >= float(cfg["cpu_hard_pct"]):
        fail("cpu_high_pct must be < cpu_hard_pct.")

    print(f"[PASS] scheduler config looks valid: {config_path}")


if __name__ == "__main__":
    main()
