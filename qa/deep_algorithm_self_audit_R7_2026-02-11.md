# Deep Algorithm Self-Audit R7

- Timestamp: 2026-02-11 10:41:10 +08:00
- Executor: Codex (GPT-5)
- Scope: respond to strict review findings, close BUG-3, and harden GPU admission consistency.

## 1) F-19 [Critical] BUG-3 closure: preserve `gpu_cards` through EMA smoothing

### Finding
When `ema_alpha < 1.0`, `_smooth_snapshot()` created a new `ResourceSnapshot` without `gpu_cards`.  
That broke GPU affinity admission because `_can_admit()` could not find target-card metadata.

### Fix
- Preserve per-card snapshot metadata during smoothing:
  - `gpu_cards=raw.gpu_cards if raw.gpu_cards is not None else prev.gpu_cards`

Code evidence:
- `prototype/resource_scheduler.py:349`
- `prototype/resource_scheduler.py:382`

Regression test:
- `prototype/tests/test_resource_scheduler.py:501`
  - `test_gpu_affinity_survives_ema_smoothing_snapshot_path`
  - Uses `ema_alpha=0.6` to force smoothing path.

## 2) F-20 [Medium] dry-run GPU projection consistency (per-card running budget)

### Finding
Dry-run admission used aggregate running GPU estimate, which could over-couple unrelated cards.

### Fix
- Introduce per-card running GPU breakdown:
  - `_running_estimated_gpu_breakdown()` returns:
    - unbound running GPU MB
    - `target_gpu_index -> running GPU MB`
- In dry-run `_can_admit()`:
  - targeted tasks use target-card running budget only (+ unbound bucket)
  - unbound tasks remain conservative

Code evidence:
- `prototype/resource_scheduler.py:397`
- `prototype/resource_scheduler.py:491`
- `prototype/resource_scheduler.py:524`

Regression tests:
- `prototype/tests/test_resource_scheduler.py:604`
  - `test_dry_run_gpu_projection_uses_per_gpu_running_budget`
- `prototype/tests/test_resource_scheduler.py:648`
  - `test_real_run_unbound_gpu_projection_remains_conservative`

## 3) Compatibility follow-up

- Keep evidence script baseline scheduler compatible with expanded `_can_admit` signature:
  - `prototype/run_patent_evidence.py:132`
  - `prototype/run_patent_evidence.py:139`

## 4) Documentation integrity fixes

- Refresh claim mapping line references after recent code shifts:
  - `qa/technique_claim_mapping_2026-02-10.md`
- Keep project progress log synchronized with timestamped checklist:
  - `logs/work_progress.md`

## 5) Verification

Commands:
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
python prototype/run_experiments.py
python prototype/run_patent_evidence.py
```

Results:
- Unit tests: `40/40` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment/evidence scripts: successful execution.

## 6) Review Checklist

- [x] BUG-3 path reproduced, fixed, and protected by smoothing-path regression test.
- [x] Dry-run GPU projection uses per-card running budget instead of global-only coupling.
- [x] Real-run per-card planned-budget behavior remains covered by tests.
- [x] Evidence scripts and mapping docs remain aligned with current code.
