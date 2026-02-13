# Deep Algorithm Self-Audit R8

- Timestamp: 2026-02-11 10:55:12 +08:00
- Executor: Codex (GPT-5)
- Scope: continue algorithm hardening while external review is in progress.

## 1) F-21 [Medium] Preemption reclaim accounting for stuck-removal path

### Problem
In emergency preemption, `_stop_task()` could return `False` even if task had already been force-removed via `TASK_STUCK_REMOVED`.  
The old reclaim loop treated that as "not reclaimed", which could trigger unnecessary extra preemption in the same tick.

### Fix
1. `_stop_task()` now updates reason-specific counters when forced removal happens:
   - `PREEMPTED` -> increment `preempted_total`
   - `TIMEOUT` -> increment `timeout_total`
2. `_preempt_low_priority()` now treats task removal from `running_set` as effective reclaim (`ok or removed`), even when stop call returns `False`.

Code evidence:
- `prototype/resource_scheduler.py:641`
- `prototype/resource_scheduler.py:657`
- `prototype/resource_scheduler.py:748`

Regression test:
- `prototype/tests/test_resource_scheduler.py:830`
  - `test_stuck_removed_counts_toward_preempt_reclaim_target`

## 2) F-22 [Medium] Pressure-aware preemption for GPU emergency

### Problem
Preemption order previously used memory estimate only.  
Under pure GPU emergency, this could evict memory-heavy but GPU-light tasks first, reducing immediate emergency relief efficiency.

### Fix
1. Detect active emergency dimensions in `_preempt_low_priority()`:
   - memory emergency (`memory/swap/available`)
   - gpu emergency (`gpu_memory_percent >= gpu_memory_emergency_pct`)
2. Add pressure-aware reclaim score:
   - memory emergency: include `estimated_mem_mb`
   - gpu emergency: include weighted `estimated_gpu_mem_mb`
   - affinity-aware weighting favors tasks on hottest GPU card.
3. Add dual reclaim goals:
   - memory reclaim target
   - gpu reclaim target (to `gpu_memory_high_pct` band)
4. Stop preemption when both active goals are satisfied.

Code evidence:
- `prototype/resource_scheduler.py:673`
- `prototype/resource_scheduler.py:695`
- `prototype/resource_scheduler.py:723`

Regression test:
- `prototype/tests/test_resource_scheduler.py:893`
  - `test_gpu_emergency_preempts_gpu_heavy_task_first`

## 3) Documentation sync

- `spec/algorithm_pseudocode.md`:
  - emergency reclaim logic updated to pressure-aware scoring and dual targets.
  - stop path now documents forced-removal metric accounting.
- `spec/data_model.md`:
  - added "Preemption Accounting (R8)" section.

## 4) Verification

Commands:
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
python prototype/run_experiments.py
python prototype/run_patent_evidence.py
```

Results:
- Unit tests: `42/42` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment/evidence scripts: successful execution.

## 5) Review Checklist

- [x] Stuck-removal path no longer causes reclaim undercount in emergency preemption.
- [x] GPU emergency preemption has direct resource-oriented ordering signal.
- [x] New behavior covered by dedicated regression tests.
- [x] Docs and implementation kept in sync.
