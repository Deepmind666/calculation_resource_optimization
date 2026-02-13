# Deep Algorithm Self-Audit R5

- Timestamp: 2026-02-11 01:06:20 +08:00
- Executor: Codex (GPT-5)
- Scope: follow-up fixes for low-level issues from R7 review (ISSUE-32/33/34/35).

## 1) ISSUE-32: `_blocked_task_ids` growth risk

### Problem
`_blocked_task_ids` could retain historical task IDs after task lifecycle ended.

### Fix
- Release blocked-task tracking when task leaves running set:
  - on normal finish (`_finish_task`)
  - on successful stop (`_stop_task`)
  - on stuck removal path

Code evidence:
- `prototype/resource_scheduler.py:347`
- `prototype/resource_scheduler.py:592`
- `prototype/resource_scheduler.py:608`

Test evidence:
- `prototype/tests/test_resource_scheduler.py:345`

## 2) ISSUE-35: no per-task observability for pending tasks in EMERGENCY

### Problem
In EMERGENCY mode, pending tasks were not attempted and produced no per-task blocked events.

### Fix
- Add per-task blocked recording for pending queue under EMERGENCY.
- Reuse unified recorder (`_record_blocked_task`) to keep metrics/events consistent.
- Event payload now carries `source` (`pending` or `admission`).

Code evidence:
- `prototype/resource_scheduler.py:264`
- `prototype/resource_scheduler.py:610`
- `prototype/resource_scheduler.py:668`

Test evidence:
- `prototype/tests/test_resource_scheduler.py:372`

## 3) ISSUE-33: data_model missing affinity fields

### Fix
- Added `gpu_cards` in `ResourceSnapshot` model docs.
- Added `target_gpu_index` in `TaskSpec` model docs.
- Added explicit R4 affinity extension section.

Doc evidence:
- `spec/data_model.md:20`
- `spec/data_model.md:37`
- `spec/data_model.md:141`

## 4) ISSUE-34: technique mapping line drift

### Fix
- Updated `qa/technique_claim_mapping_2026-02-10.md` with current implementation line references for C1/C2.

Doc evidence:
- `qa/technique_claim_mapping_2026-02-10.md:10`
- `qa/technique_claim_mapping_2026-02-10.md:12`

## 5) Verification

Commands:
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```

Results:
- Unit tests: `36/36` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.

## 6) Review Checklist

- [x] Each issue has concrete code/doc change and line evidence.
- [x] New runtime behavior has direct regression tests.
- [x] Mapping references were revalidated after code movement.
- [x] No high-risk behavior change outside scoped issues.
