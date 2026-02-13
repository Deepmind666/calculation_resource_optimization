# Deep Algorithm Self-Audit R3

- Timestamp: 2026-02-11 00:48:24 +08:00
- Executor: Codex (GPT-5)
- Scope: blocked metric semantics and observability consistency.

## 1) Problem

`blocked_total` represented event count only. In repeated blocking scenarios, users could not directly read "how many unique tasks were blocked" from scheduler metrics.

This caused metric ambiguity in reviews and experiment reports.

## 2) Improvement

### F-16 [Medium] Split blocked metrics into event and unique-task dimensions
- Added `blocked_task_total` to scheduler metrics.
- Added scheduler-level unique blocked task tracking set.
- Counting rule:
  - `blocked_total`: increment on every block event.
  - `blocked_task_total`: increment once per task ID across scheduler lifetime.

Code evidence:
- `prototype/resource_scheduler.py:94`
- `prototype/resource_scheduler.py:208`
- `prototype/resource_scheduler.py:281`

## 3) Regression Coverage

New tests:
- `prototype/tests/test_resource_scheduler.py:307`
- `prototype/tests/test_resource_scheduler.py:326`

Validation behavior:
1. Same task blocked on multiple ticks:
   - `blocked_total` grows per tick.
   - `blocked_task_total` remains 1.
2. Multiple tasks blocked in one tick:
   - `blocked_total == blocked_task_total == number_of_tasks`.

## 4) Downstream Sync

- Experiment script now exports both dimensions:
  - `prototype/run_experiments.py`
  - output files regenerated:
    - `figures/scheduler_experiment_metrics.csv`
    - `figures/scheduler_experiment_metrics.json`

- Spec sync:
  - `spec/algorithm_pseudocode.md`
  - `spec/data_model.md`

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
- Unit tests: `32/32` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment and evidence scripts: executed successfully and regenerated outputs.

## 6) Review Checklist

- [x] Metric semantics are explicit and non-ambiguous.
- [x] Existing `blocked_total` backward compatibility preserved.
- [x] New metric has direct tests for repeated and multi-task blocking.
- [x] Spec and experiment outputs synchronized with implementation.
