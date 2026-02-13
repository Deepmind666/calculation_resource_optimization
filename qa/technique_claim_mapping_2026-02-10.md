# Technique-Claim Mapping (Resource Scheduler)

- Timestamp: 2026-02-11 11:08:22 +08:00
- Executor: Codex (GPT-5)
- Purpose: map code lines -> technical feature -> claim candidate -> evidence.

## Mapping Table

| Claim Candidate | Technical Feature | Implementation Evidence | Experiment Evidence | Regression Test |
|---|---|---|---|---|
| C1 (P-02) | Dual-view mode decision: emergency uses raw snapshot, steady-state uses EMA plus hysteresis plus cooldown | `prototype/resource_scheduler.py:432`, `prototype/resource_scheduler.py:441`, `prototype/resource_scheduler.py:455` | `prototype/run_patent_evidence.py:161`, `prototype/run_patent_evidence.py:176`, `prototype/run_patent_evidence.py:195` | `prototype/tests/test_patent_evidence.py:17` |
| C1-Baseline | Comparator: EMA-only (alpha=0.3), no raw bypass for emergency | `prototype/run_patent_evidence.py:69` | `prototype/run_patent_evidence.py:161`, `prototype/run_patent_evidence.py:177`, `prototype/run_patent_evidence.py:195` | `prototype/tests/test_patent_evidence.py:17` |
| C2 (P-03) | Same-tick cumulative projection: each admitted task contributes planned_extra before next decision | `prototype/resource_scheduler.py:260`, `prototype/resource_scheduler.py:301`, `prototype/resource_scheduler.py:315`, `prototype/resource_scheduler.py:496`, `prototype/resource_scheduler.py:533` | `prototype/run_patent_evidence.py:230`, `prototype/run_patent_evidence.py:251`, `prototype/run_patent_evidence.py:274` | `prototype/tests/test_patent_evidence.py:28` |
| C2-Baseline | Comparator: no cumulative projection, each task judged against static snapshot | `prototype/run_patent_evidence.py:129` | `prototype/run_patent_evidence.py:230`, `prototype/run_patent_evidence.py:253`, `prototype/run_patent_evidence.py:294` | `prototype/tests/test_patent_evidence.py:28` |

## Quantified Effects

1. P-02 emergency response delay:
   - `dual_view_raw_plus_ema`: delay = 0 tick.
   - `ema_only_alpha_0_3_no_raw_bypass`: delay = 3 ticks.
2. P-03 over-issue risk:
   - `with_cumulative_projection`: admitted = 2, peak = 90.8906% (< 92%).
   - `without_cumulative_projection_baseline`: admitted = 4, peak = 100.6562% (>= 92%).
   - `over_issue_rate_without_cumulative = 0.5`.

## Review Checklist

- [x] Every claim candidate has implementation + experiment + test mapping.
- [x] P-02 uses the requested EMA-only comparator (alpha=0.3, no raw bypass).
- [x] P-03 uses the requested no-cumulative comparator at scheduler level.
- [x] Results are reproducible via `python prototype/run_patent_evidence.py`.
- [x] Line references were refreshed against current code after latest scheduler changes.
