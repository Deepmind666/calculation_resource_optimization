# Patent Claim Feature Alignment (R42)

- Timestamp: 2026-02-14 18:17:31 +08:00
- Purpose: align patent claim restoration artifacts with implemented scheduling features
- Scope: documentation alignment only, no runtime behavior changes

## 1. Core Feature Baseline

1. Dual-view mode decision:
   - Emergency decision uses raw snapshot.
   - Steady-state decision uses smoothed snapshot with hysteresis/cooldown.
2. Same-cycle cumulative admission projection:
   - Accepted tasks update later-candidate projection baseline in the same cycle.
3. Per-GPU budget with bound/unbound split:
   - Bound task projects to target GPU.
   - Unbound task contributes conservatively.
4. Emergency reclaim:
   - Bottleneck dimension + hotspot GPU identification.
   - Normalized multi-resource reclaim scoring.
   - Dual-goal stop condition.

## 2. Patent Draft Alignment Targets

1. `v8` keeps the compact independent-claim shape for first-round readability.
2. `R41` restoration packs provide add-back clauses by office-action type.
3. `R42` full renumbered sample re-materializes add-back clauses into complete claim set.

## 3. Out-of-Scope

1. No updates to `prototype/resource_scheduler.py`.
2. No algorithm threshold changes.
3. No experiment reruns in this round.
