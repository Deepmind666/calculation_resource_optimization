# Deep Algorithm Self-Audit R4

- Timestamp: 2026-02-11 00:57:16 +08:00
- Executor: Codex (GPT-5)
- Scope: task-level GPU affinity admission prediction.

## 1) Motivation

Current scheduler uses the riskiest GPU card for guard decisions. This is safe but can over-block tasks that are explicitly bound to a different low-load card.

## 2) Improvement

### F-17 [Medium] Add task-level GPU affinity for admission projection
- Added `TaskSpec.target_gpu_index: Optional[int]`.
- Added `ResourceSnapshot.gpu_cards` to carry per-card memory snapshots.
- Monitor now parses all cards and keeps per-card metrics in `gpu_cards`.
- Admission logic update:
  - If `target_gpu_index` is set, project GPU load on that target card.
  - If target index is unavailable, reject with explicit reason.
  - If no target is set, keep existing riskiest-card behavior.

Code evidence:
- `prototype/resource_scheduler.py:30`
- `prototype/resource_scheduler.py:41`
- `prototype/resource_scheduler.py:157`
- `prototype/resource_scheduler.py:443`
- `prototype/resource_scheduler.py:678`

## 3) Regression Coverage

Added tests:
- `prototype/tests/test_resource_scheduler.py:227`
  - Reject invalid negative affinity index in task spec.
- `prototype/tests/test_resource_scheduler.py:414`
  - Same snapshot: no-affinity blocks, target-card affinity admits.
- `prototype/tests/test_resource_scheduler.py:453`
  - Invalid target index is rejected with explicit reason.

Extended monitor test:
- `prototype/tests/test_resource_scheduler.py:375`
  - Verifies `gpu_cards` is exported with per-card memory percentages.

## 4) Verification

Commands:
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```

Results:
- Unit tests: `34/34` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.

## 5) Review Checklist

- [x] Feature is backward compatible for tasks without affinity.
- [x] Affinity out-of-range is explicit fail, not silent fallback.
- [x] Per-card monitor data is available to scheduler admission path.
- [x] New behavior has direct tests for positive and negative paths.
