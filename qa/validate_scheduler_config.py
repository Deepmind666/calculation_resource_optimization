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


def main() -> None:
    if not CONFIG.exists():
        fail(f"Missing config: {CONFIG}")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    required_keys = {
        "max_workers",
        "min_workers",
        "memory_high_pct",
        "memory_emergency_pct",
        "cpu_high_pct",
        "cpu_hard_pct",
        "reserve_memory_mb",
        "dry_run",
    }
    missing = sorted(required_keys - set(cfg.keys()))
    if missing:
        fail(f"Missing keys: {missing}")

    if not (cfg["min_workers"] >= 1 and cfg["max_workers"] >= cfg["min_workers"]):
        fail("Invalid worker range.")

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

    print("[PASS] scheduler config looks valid.")


if __name__ == "__main__":
    main()
