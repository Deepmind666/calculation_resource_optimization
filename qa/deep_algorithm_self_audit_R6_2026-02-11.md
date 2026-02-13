# Deep Algorithm Self-Audit R6

- Timestamp: 2026-02-11 09:18:24 +08:00
- Executor: Codex (GPT-5)
- Scope: next-stage algorithm enhancement after R7 PASS.

## 1) F-18 [Medium] Per-GPU planned budget for same-tick admission

### Problem
With task-level affinity, same-tick GPU planned load was still tracked in a single global scalar.  
That could over-block a task on `GPU-0` because of planned load that actually belongs to `GPU-1`.

### Fix
- Replace scalar `planned_extra_gpu_mb` with split budget:
  - `planned_extra_gpu_by_index`
  - `planned_extra_gpu_unbound_mb`
- In `_can_admit`:
  - targeted task -> apply unbound budget + target-card budget only
  - unbound task -> keep conservative behavior using all known per-card budgets

Code evidence:
- `prototype/resource_scheduler.py:262`
- `prototype/resource_scheduler.py:300`
- `prototype/resource_scheduler.py:466`
- `prototype/resource_scheduler.py:487`
- `prototype/resource_scheduler.py:518`

Compatibility sync:
- `prototype/run_patent_evidence.py:139`

### Tests
- `prototype/tests/test_resource_scheduler.py:529`
  - Targeted task is not over-blocked by planned load on another card.
- `prototype/tests/test_resource_scheduler.py:564`
  - Unbound task remains conservative under cross-card planned load.

## 2) R7 low-issue closure carried forward in this round

- ISSUE-32 lifecycle cleanup for `_blocked_task_ids`:
  - `prototype/resource_scheduler.py:568`
  - `prototype/resource_scheduler.py:607`
  - `prototype/resource_scheduler.py:620`
- ISSUE-35 per-task observability under EMERGENCY:
  - `prototype/resource_scheduler.py:264`
  - `prototype/resource_scheduler.py:689`
  - `prototype/tests/test_resource_scheduler.py:389`

## 3) Verification

Commands:
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
python prototype/run_experiments.py
python prototype/run_patent_evidence.py
```

Results:
- Unit tests: `38/38` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment and evidence scripts: successful.

## 4) Review Checklist

- [x] Per-GPU same-tick projection no longer mixes cross-card load for targeted tasks.
- [x] Unbound tasks still use conservative guard path.
- [x] R7 low issues remain closed after this enhancement.
- [x] Full regression remains green.
