# Deep Algorithm Self-Audit R12

- Timestamp: 2026-02-11 12:47:27 +08:00
- Executor: Codex (GPT-5)
- Scope: close R12 test blind spots (real process, long-run robustness, estimation-error behavior).

## 1) F-27 [Test] Real-process lifecycle coverage

### Gap
Previous suite had limited end-to-end validation for real subprocess lifecycle.

### Added coverage
1. `test_real_process_completes_and_is_accounted`
   - Starts a real subprocess (`dry_run=False`).
   - Verifies completion path, running-set cleanup, and `TASK_FINISHED/COMPLETED`.
2. `test_real_process_timeout_stops_process_object`
   - Starts a long real subprocess with tiny `max_runtime_sec`.
   - Verifies timeout stop path, running-set cleanup, and non-`None` process poll result.

Evidence:
- `prototype/tests/test_resource_scheduler.py:1153`
- `prototype/tests/test_resource_scheduler.py:1190`

## 2) F-28 [Test] Long-run randomized robustness coverage

### Gap
No medium/long horizon test to detect state drift under noisy inputs.

### Added coverage
`test_long_run_randomized_snapshots_preserve_state_invariants`
- 220 ticks with deterministic random snapshots (`seed=12345`).
- Incremental task submissions and invariant checks per tick:
  - `report.running_count == len(running)`
  - `report.pending_count == len(pending)`
  - `len(running) <= max_workers`
  - event log bounded
  - metrics monotonic sanity
  - pending task IDs unique

Evidence:
- `prototype/tests/test_resource_scheduler.py:1233`

## 3) F-29 [Test] Estimation-error behavior coverage

### Gap
No explicit tests for overestimate/underestimate scenarios.

### Added coverage
1. `test_estimation_error_overestimate_blocks_large_task_but_small_task_runs`
   - Overestimated large task is blocked while small task still starts (progress is preserved).
2. `test_estimation_error_underestimate_then_raw_spike_preempts`
   - Underestimated running task is later preempted when raw emergency spike appears.

Evidence:
- `prototype/tests/test_resource_scheduler.py:1276`
- `prototype/tests/test_resource_scheduler.py:1312`

## 4) Stability re-check (anti-flake)

Repeated-run checks executed:
1. Long-run randomized test x5: all passed.
2. Real-process completion+timeout tests x5: all passed.

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
- Unit tests: `51/51` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.
- Experiment/evidence scripts: successful execution.
- Mapping reference audit: `ALL_MAPPING_REFS_VALID`.

## 6) Review Checklist

- [x] Real subprocess completion path is explicitly tested.
- [x] Real subprocess timeout/stop path is explicitly tested.
- [x] Long-run noisy-sequence invariants are covered.
- [x] Estimation over/under error behaviors are covered.
- [x] Repeated-run anti-flake checks passed.
