# Deep Algorithm Self-Audit R10

- Timestamp: 2026-02-11 11:08:22 +08:00
- Executor: Codex (GPT-5)
- Scope: continue post-R9 algorithm hardening while parallel external review is running.

## 1) F-23 [Medium] Dry-run admission cache to remove repeated `running_set` full scans

### Problem
`_can_admit()` called `_running_estimated_load()` and `_running_estimated_gpu_breakdown()` on each admission attempt in dry-run mode.  
Under high queue pressure this creates repeated O(N) scans in a single tick.

### Fix
1. In `tick()` precompute dry-run running estimates once:
   - `running_est_mem_mb`
   - `running_est_cpu_pct`
   - `running_gpu_unbound_mb`
   - `running_gpu_by_index`
2. Pass these values into `_can_admit()` as optional arguments.
3. After each successful start, increment cache values in-place so same-tick projections remain correct.
4. Keep `_can_admit()` fallback path for direct calls/tests when no cache is provided.

Code evidence:
- `prototype/resource_scheduler.py:264`
- `prototype/resource_scheduler.py:301`
- `prototype/resource_scheduler.py:496`
- `prototype/resource_scheduler.py:517`

Regression test:
- `prototype/tests/test_resource_scheduler.py:852`
  - `test_dry_run_running_estimate_computed_once_per_tick`
  - Asserts both estimate functions are called once during a multi-start tick.

## 2) F-24 [Medium] Add `ema_alpha<1.0` full-path integration test

### Problem
Prior coverage proved isolated branches, but lacked a full tick-path integration for:
- EMA smoothing active (`ema_alpha<1.0`)
- affinity admission
- raw GPU emergency trigger
- emergency preemption chain

### Fix
Add integrated test across three ticks:
1. Tick-1 seed EMA state.
2. Tick-2 admit affinity-bound GPU task in normal mode.
3. Tick-3 raise raw GPU emergency and assert preemption.

Test evidence:
- `prototype/tests/test_resource_scheduler.py:219`
  - `test_ema_alpha_full_tick_path_gpu_affinity_then_emergency_preempt`

## 3) Compatibility maintenance

Synchronize ablation baseline override signature to new scheduler API:
- `prototype/run_patent_evidence.py:132`

## 4) Documentation sync

- `spec/algorithm_pseudocode.md`
  - Added dry-run per-tick running-estimate cache behavior in admission loop.
- `spec/data_model.md`
  - Added `Dry-Run Admission Cache (R9)` notes.

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
- Unit tests: `44/44` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment/evidence scripts: successful execution.

## 6) Review Checklist

- [x] Dry-run projection correctness preserved while reducing repeated scans.
- [x] `ema_alpha<1.0` integrated path now has explicit regression coverage.
- [x] Evidence/ablation script API compatibility retained.
- [x] Code, tests, and docs remain synchronized.
