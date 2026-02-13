# Deep Algorithm Self-Audit R11

- Timestamp: 2026-02-11 12:42:18 +08:00
- Executor: Codex (GPT-5)
- Scope: close ISSUE-36 and ISSUE-37, then run full regression/self-audit.

## 1) F-25 [Low] ISSUE-36 closure: preemption emergency dimension uses raw view

### Problem
`_evaluate_mode()` uses raw snapshot for emergency triggers, but `_preempt_low_priority()` previously inferred emergency dimensions from smoothed snapshot.  
In a raw spike + smoothed lag scenario, preemption could degrade from GPU-aware ordering to memory-only ordering.

### Fix
1. `tick()` passes raw snapshot into preemption path.
2. `_preempt_low_priority(snapshot, raw_snapshot=None)` introduced.
3. `emergency_view = raw_snapshot or snapshot`, and emergency dimensions are derived from `emergency_view`.

Code evidence:
- `prototype/resource_scheduler.py:255`
- `prototype/resource_scheduler.py:694`
- `prototype/resource_scheduler.py:702`

Regression test:
- `prototype/tests/test_resource_scheduler.py:1027`
  - `test_preempt_uses_raw_view_for_emergency_dimension_detection`

## 2) F-26 [Low] ISSUE-37 closure: mixed emergency score normalization

### Problem
Mixed emergency scoring previously added memory MB and GPU MB directly.  
This mixes units and can bias ordering toward whichever raw magnitude is larger.

### Fix
1. Keep `effective_gpu_reclaim` affinity weights.
2. Normalize each component by current reclaim gap:
   - `mem_score = estimated_mem_mb / max(1, reclaim_needed_mem_mb)`
   - `gpu_score = effective_gpu_reclaim / max(1, reclaim_needed_gpu_mb)`
3. Combined score uses normalized sum, preserving interpretability and reducing unit bias.

Code evidence:
- `prototype/resource_scheduler.py:744`
- `prototype/resource_scheduler.py:745`
- `prototype/resource_scheduler.py:759`

Regression test:
- `prototype/tests/test_resource_scheduler.py:1093`
  - `test_mixed_emergency_preempt_score_uses_normalized_resources`

## 3) Self-check found and fixed one regression during this round

### Observation
Initial cooldown guard returned early whenever both reclaim targets were zero.  
This broke two legacy direct-call tests that intentionally call `_preempt_low_priority()` without raw context.

### Correction
Guard refined to apply only for tick-path calls (where `raw_snapshot` is provided):
- `if raw_snapshot is not None and not memory_emergency and not gpu_emergency: return []`

This keeps cooldown over-preemption protection while preserving direct-call test behavior.

Code evidence:
- `prototype/resource_scheduler.py:741`

## 4) Documentation sync

- `spec/algorithm_pseudocode.md`
  - preemption pseudocode now includes `raw_snapshot` emergency view and normalized score concept.
- `spec/data_model.md`
  - added `Emergency Preemption View and Score (R11)` section.

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
- Unit tests: `46/46` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment/evidence scripts: successful execution.
- Claim mapping line-reference audit: `ALL_MAPPING_REFS_VALID`.

## 6) Review Checklist

- [x] ISSUE-36 closed with code + regression test.
- [x] ISSUE-37 closed with normalized scoring + regression test.
- [x] Mid-round regression detected and repaired before finalization.
- [x] Code/tests/docs remain synchronized after changes.
