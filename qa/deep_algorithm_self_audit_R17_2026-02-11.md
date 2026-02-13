# Deep Algorithm Self Audit R17 (2026-02-11)

- Timestamp: 2026-02-11 18:24:05 +08:00
- Owner: Codex (GPT-5)
- Scope: R17 algorithm enhancement for dual-emergency preemption scoring

## 1) Problem Addressed

In mixed emergencies (memory + GPU), previous normalized scoring could still over-favor one-sided victims (high reclaim on one resource, near-zero on the other). Under tight preemption budgets, this may reduce recovery efficiency.

## 2) Algorithm Changes

1. `prototype/resource_scheduler.py`
- Updated `_preempt_low_priority()` -> `resource_reclaim_score()`.
- New mixed-emergency scoring rule:
  - `mem_norm = estimated_mem_mb / reclaim_needed_mem_mb`
  - `gpu_norm = effective_gpu_reclaim / reclaim_needed_gpu_mb`
  - when both dimensions are emergency:
    - `mem_unit = min(1.0, mem_norm)`
    - `gpu_unit = min(1.0, gpu_norm)`
    - `score = mem_unit + gpu_unit + min(mem_unit, gpu_unit)`
- Rationale:
  - keep normalization (no unit mixing)
  - cap one-dimensional overflow gains
  - add synergy bonus for victims that relieve both bottlenecks

## 3) Test Additions

1. `prototype/tests/test_resource_scheduler.py`
- Added `test_mixed_emergency_prefers_dual_reclaim_contributor`:
  - constructs a case where one task is memory-only heavy and another contributes to both memory+GPU;
  - asserts scheduler preempts the dual-contributor in mixed emergency.

## 4) Verification Checklist (Executed)

1. Targeted tests
- `python -m unittest prototype.tests.test_resource_scheduler.ResourceSchedulerTests.test_mixed_emergency_preempt_score_uses_normalized_resources -v` -> PASS
- `python -m unittest prototype.tests.test_resource_scheduler.ResourceSchedulerTests.test_mixed_emergency_prefers_dual_reclaim_contributor -v` -> PASS

2. Full regression
- `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (59/59)

3. Structural/config checks
- `python qa/validate_scheduler_config.py spec/scheduler_config.example.json` -> PASS
- `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS

4. Experiment regression
- `python prototype/run_experiments.py` -> PASS
- `python prototype/run_patent_evidence.py` -> PASS
- `python prototype/run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5` -> PASS

## 5) Quantitative Outcomes (R17)

1. P-04 (unchanged, stability check)
- per-GPU false-block rate: `0.0`
- aggregate false-block rate: `0.182961`

2. P-05 full-limit
- avg preemptions:
  - normalized: `3.6864`
  - raw_mb: `3.886`
  - random: `3.8641`

3. P-05 tight-limit (k=5)
- avg preemptions:
  - normalized: `3.5164`
  - raw_mb: `3.6456`
  - random: `3.6825`
- recovery rate:
  - normalized: `0.913`
  - raw_mb: `0.872`
  - random: `0.89855`
- tight recovery advantage:
  - vs raw: `+0.041`
  - vs random: `+0.01445`

## 6) File Review Checklist

- [x] algorithm change is localized and test-backed
- [x] no regression in existing scheduler behavior tests
- [x] full suite + config + structure all green
- [x] experiment metrics regenerated and consistent with code behavior
- [x] changes recorded for handoff and external review

## 7) Risks and Follow-up

1. Risk
- Scoring coefficients are heuristic; different workload distributions may favor different tradeoffs.

2. Follow-up
- Add multi-seed confidence interval reporting for P-05 tight-limit metrics.
- Optionally expose mixed-emergency scoring parameters in config for controlled tuning.
