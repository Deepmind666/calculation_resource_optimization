# Deep Algorithm Self Audit R18 (2026-02-11)

- Timestamp: 2026-02-11 18:43:37 +08:00
- Owner: Codex (GPT-5)
- Scope: Multi-seed confidence interval framework for advanced scheduler evidence (P-04/P-05)

## 1) Changes Implemented

1. `prototype/run_advanced_research.py`
- Added CI utility `_mean_ci95(values)`.
- Added `run_multiseed_confidence_summary(...)`:
  - repeated runs over deterministic seed ladder
  - outputs per-seed metrics and aggregated mean/stddev/95% CI.
- Added CLI options:
  - `--multi-seed-runs`
  - `--multi-seed-trials`
  - `--multi-seed-step`
- Extended payload and CSV flattening:
  - JSON adds `multiseed` block
  - CSV adds `MULTI-SEED-CI` rows.

2. `prototype/tests/test_advanced_research.py`
- Added `test_multiseed_confidence_summary_has_ci_bounds`:
  - checks output structure
  - checks CI monotonicity (`ci95_low <= mean <= ci95_high`)
  - checks per-seed cardinality.

3. Documentation
- `prototype/README.md`: appended multi-seed CI usage section.
- `figures/README.md`: appended multi-seed output description.

## 2) Verification Checklist (Executed)

1. Targeted tests
- `python -m unittest prototype.tests.test_advanced_research -v` -> PASS (3/3)

2. Full tests
- `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (60/60)

3. Config/structure
- `python qa/validate_scheduler_config.py spec/scheduler_config.example.json` -> PASS
- `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS

4. Script regressions
- `python prototype/run_experiments.py` -> PASS
- `python prototype/run_patent_evidence.py` -> PASS

5. Multi-seed execution sample
- Command:
  `python prototype/run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5 --multi-seed-runs 7 --multi-seed-trials 5000 --multi-seed-step 9973`
- Result: PASS and artifacts regenerated.

## 3) Key Quantitative Outputs (R18)

1. Single-run anchor (trials=20000)
- P-04 false_block_reduction: `0.182961`
- P-05 tight recovery advantage:
  - vs raw: `+0.041`
  - vs random: `+0.01445`

2. Multi-seed CI (7 runs, 5000 trials/seed)
- `p04_false_block_reduction` mean `0.186426`, 95% CI `[0.180939, 0.191913]`
- `p05_tight_recovery_advantage_vs_raw` mean `0.036571`, 95% CI `[0.035565, 0.037578]`
- `p05_tight_recovery_advantage_vs_random` mean `0.012486`, 95% CI `[0.009903, 0.015069]`
- `p05_recovery_rate_normalized_tight` mean `0.908571`, 95% CI `[0.904694, 0.912449]`

## 4) Reviewer Notes

1. CI intervals are narrow in this run setting, indicating stable directional advantage for normalized strategy under tight preemption budget.
2. `p04_false_block_reduction` equals `p04_aggregate_false_block_rate` currently because per-GPU false-block remains `0.0`; both are kept for transparency.

## 5) Files Changed in R18

1. `prototype/run_advanced_research.py`
2. `prototype/tests/test_advanced_research.py`
3. `prototype/README.md`
4. `figures/README.md`
5. `figures/advanced_research_metrics.csv`
6. `figures/advanced_research_metrics.json`
7. `figures/scheduler_experiment_metrics.csv`
8. `figures/scheduler_experiment_metrics.json`
9. `figures/patent_evidence_metrics.csv`
10. `figures/patent_evidence_metrics.json`

## 6) Risks and Next Steps

1. Risk
- Current CI assumes independent seeds and fixed synthetic workload generator; real-machine CI is still pending.

2. Next steps
- Add optional repeated real-baseline mode with controlled cooldown between runs.
- Export CI summaries into dedicated review-friendly markdown table for patent evidence package.
