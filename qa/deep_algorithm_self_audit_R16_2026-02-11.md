# Deep Algorithm Self Audit R16 (2026-02-11)

- Timestamp: 2026-02-11 18:01:20 +08:00
- Owner: Codex (GPT-5)
- Scope: R16 experiment-rigor upgrade for P-04/P-05 evidence quality

## 1) Changes Implemented

1. `prototype/run_advanced_research.py`
- Upgraded P-04 from single-case interference to mixed scenario buckets:
  - `other_card_only`
  - `same_card_only`
  - `mixed_cards`
  - `no_planned_budget`
- Added per-scenario breakdown metrics (`scenario_breakdown`) in JSON output.
- Upgraded P-05 to include two variants in one run:
  - full-limit baseline (all candidates reachable)
  - tight-limit stress variant (`tight_preempt_limit`, default 5)
- Added CLI flag: `--p05-tight-preempt-limit`.
- Extended CSV flatten output with:
  - P-04 scenario rows (`P-04-SCENARIO`)
  - P-05 tight-limit row (`P-05-TIGHT`)

2. `prototype/tests/test_advanced_research.py`
- Added assertions for P-04 breakdown integrity:
  - sum of scenario trials equals total trials
  - sum of scenario safe cases equals total safe cases
  - other-card scenario aggregate false-block rate exceeds per-GPU rate
- Added assertions for P-05 tight-limit output fields and baseline behavior.

3. Documentation touch-ups
- `prototype/README.md`: appended R16 advanced research update section.
- `figures/README.md`: appended R16 metric-field update note.

## 2) Verification Checklist (Executed)

1. Unit tests
- Command: `python -m unittest prototype.tests.test_advanced_research -v`
- Result: PASS (2/2)

2. Full test suite
- Command: `python -m unittest discover -s prototype/tests -p "test_*.py"`
- Result: PASS (58/58)

3. Config validation
- Command: `python qa/validate_scheduler_config.py spec/scheduler_config.example.json`
- Result: PASS

4. Structure validation
- Command: `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1`
- Result: PASS

5. Regression scripts
- Command: `python prototype/run_experiments.py`
- Result: PASS, CSV/JSON regenerated
- Command: `python prototype/run_patent_evidence.py`
- Result: PASS, CSV/JSON regenerated

6. Advanced research (large run)
- Command:
  `python prototype/run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5 --run-real-baseline --real-task-count 24 --real-task-duration-sec 2.0 --real-base-mem-mb 96 --real-fixed-workers 6`
- Result: PASS, CSV/JSON regenerated

## 3) Key Measured Outcomes (Large Run)

1. P-04 overall
- `safe_cases`: 16222 / 20000
- `per_gpu_false_block_rate`: 0.0
- `aggregate_false_block_rate`: 0.182961
- `false_block_reduction`: 0.182961

2. P-04 scenario breakdown highlights
- `other_card_only`: aggregate false-block 0.376155 vs per-GPU 0.0
- `mixed_cards`: aggregate false-block 0.346585 vs per-GPU 0.0
- `same_card_only`: both 0.0
- `no_planned_budget`: both 0.0

3. P-05 full-limit
- normalized avg preemptions: 3.7551
- raw MB avg preemptions: 3.886
- random avg preemptions: 3.8641
- all variants recovery rate: 1.0 (expected under full reachability)

4. P-05 tight-limit (k=5)
- normalized avg preemptions: 3.5421
- raw MB avg preemptions: 3.6456
- random avg preemptions: 3.6825
- recovery rates: normalized 0.88575, raw 0.872, random 0.89855
- note: normalized improves over raw in both efficiency and recovery, but random still has slightly higher recovery in this setup due more aggressive victim spread.

## 4) Self-Check Risks and Findings

1. Risk: P-05 tight-limit interpretation may still be debated because random strategy can trade higher preemption breadth for higher recovery in some distributions.
- Mitigation applied: output now includes both recovery and preemption count, avoiding single-metric over-claim.

2. Risk: Real baseline `peak_memory_pct`/`peak_swap_pct` can be `null` if `psutil` is unavailable in runtime environment.
- Current status: observed as `null` in this run; script remains stable and records other metrics.
- Next candidate fix: explicit environment flag + fallback sampler warning row.

3. Regression risk: none observed in 58-test run and script regressions.

## 5) Files Changed in R16

1. `prototype/run_advanced_research.py`
2. `prototype/tests/test_advanced_research.py`
3. `prototype/README.md`
4. `figures/README.md`

## 6) Ready for External Review

- This round is review-ready.
- All claims above are backed by executable commands and regenerated artifacts under `figures/`.
