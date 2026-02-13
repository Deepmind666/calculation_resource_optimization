# Deep Algorithm Self-Audit R2

- Timestamp: 2026-02-10 17:41:33 +08:00
- Executor: Codex (GPT-5)
- Scope: `prototype/resource_scheduler.py`, `qa/validate_scheduler_config.py`, scheduler test suite.
- Goal: run a deeper fault-oriented audit, fix proven issues, and keep changes fully reproducible.

## 1) Audit Method

1. Static inspection of emergency path, admission control path, preemption path, and config validation.
2. Fault injection for GPU monitor parsing with mixed valid/malformed `nvidia-smi` rows.
3. Boundary validation for threshold relations in config.
4. Full regression (`unittest` + config validator + structure check).

## 2) Proven Issues and Fixes

### F-14 [High] GPU guard could be silently disabled by malformed `nvidia-smi` row
- Reproduction (before fix): mixed output with one `N/A` row caused `_sample_gpu()` to return `{}`.
- Risk: GPU emergency/high guard could be bypassed even when valid GPU rows exist.
- Fix:
  - Parse each row independently.
  - Skip malformed rows instead of failing whole sampling.
  - Skip non-positive `memory.total` rows.
- Code evidence:
  - `prototype/resource_scheduler.py:153`
  - `prototype/resource_scheduler.py:179`
- Test evidence:
  - `prototype/tests/test_resource_scheduler.py:338`

### F-15 [Medium] Missing GPU threshold relation validation (`high < emergency`)
- Reproduction (before fix): config with `gpu_memory_high_pct=96`, `gpu_memory_emergency_pct=95` passed validation.
- Risk: mode logic semantics become inconsistent; `HIGH` threshold above `EMERGENCY` threshold is invalid policy.
- Fix:
  - Add relation check in core config validation.
  - Add same relation check in QA validator script.
- Code evidence:
  - `prototype/resource_scheduler.py:709`
  - `qa/validate_scheduler_config.py:110`
- Test evidence:
  - `prototype/tests/test_resource_scheduler.py:555`

## 3) Validation Results

Commands:
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```

Results:
- Unit tests: `30/30` passed.
- Config validation: `PASS`.
- Structure check: `PASS`.

## 4) File-Level Review Checklist

- [x] Every fix has a deterministic reproduction scenario.
- [x] Every fix has at least one dedicated regression test.
- [x] Core validation and QA validation logic are kept consistent.
- [x] No unrelated rollback or destructive git operation was used.
- [x] Full regression and structure checks passed after edits.

## 5) Residual Risks (Not Fixed in This Round)

- `blocked_total` still measures event count, not unique blocked task count.
- Multi-GPU admission is risk-card based; no task-level GPU affinity projection yet.
