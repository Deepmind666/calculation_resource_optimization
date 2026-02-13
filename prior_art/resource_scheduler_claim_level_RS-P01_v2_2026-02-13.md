# RS-P01 Claim-Level Comparison v2 (US11656911B2 / US20200167197A1)

- Timestamp: 2026-02-13 14:20:00 +08:00
- Owner: Codex (GPT-5)
- Review target: ISSUE-55 (claim-level comparison not complete)
- Scope: Independent claims of RS-P01 family vs current local-resource scheduler

## 1. Primary Sources (direct URLs)

1. US11656911B2 (granted): https://patents.google.com/patent/US11656911B2/en
2. US20200167197A1 (application): https://patents.google.com/patent/US20200167197A1/en

Verification note:
- This file is based on the claim sections shown on Google Patents (independent claim structure cross-checked on the grant page).
- This is an engineering claim chart for risk control, not legal advice.

## 2. Independent Claim Elementization

### 2.1 Claim 1 (system, US11656911B2)

E1. Discover running workloads in a compute cloud.
E2. Discover pending workloads.
E3. Determine capacity is insufficient for pending workloads.
E4. Define service-level target (SLT) policy for workloads.
E5. Detect excessive allocation relative to an SLT-driven threshold.
E6. Preemptively terminate (evict) part of running workloads.
E7. Schedule pending + evicted workloads to computing resources outside the original cloud.

### 2.2 Claim 16 (method, US11656911B2)

M1. Detect running workloads.
M2. Detect pending workloads.
M3. Determine insufficient capacity.
M4. Define target policy/threshold relation.
M5. Identify over-allocation.
M6. Preemptively terminate subset of running workloads.
M7. Reschedule workloads to other resources.

### 2.3 Claim 18 (non-transitory medium, US11656911B2)

C1. Program instructions implementing the same chain as Claim 16.

## 3. Element-by-Element Comparison to Current Project

Current implementation references:
- prototype/resource_scheduler.py
- prototype/run_advanced_research.py
- prototype/tests/test_resource_scheduler.py
- prototype/tests/test_advanced_research.py

| RS-P01 element | Coverage in our code | Overlap risk | Engineering assessment |
|---|---|---|---|
| E1/M1 resource discovery | Present (local CPU/mem/GPU snapshots) | Medium | Similar monitoring intent, but local-host model (not cloud control plane). |
| E2/M2 pending workload queue | Present | Medium | We maintain pending queue and admission loop. |
| E3/M3 capacity insufficiency | Present | Medium | Triggered by multi-mode thresholds and admission projection. |
| E4/M4 SLT policy engine | Not present (different abstraction) | Low-Medium | We do not implement per-task SLT contracts as core policy primitive. |
| E5/M5 threshold overload check | Present (different formula family) | Medium | We use raw+EMA mode logic + hysteresis/cooldown + per-resource limits. |
| E6/M6 preemptive termination | Present | High | This is the strongest overlap with RS-P01 family. |
| E7/M7 re-scheduling to other resources | Partial | Medium | We re-admit under guardrails, but no explicit "other cloud" migration model. |
| C1 medium claim | Partial | Medium | Software medium form overlaps structurally, details differ. |

## 4. High-Risk and Differentiation Summary

### 4.1 High-risk overlap (must acknowledge)

1. "Detect overload -> preempt running tasks -> continue scheduling" control chain is substantially similar to RS-P01 family intent.
2. CP-2 (resource-aware preemption) by itself is not safe as a standalone claim anchor.

### 4.2 Differentiation bundle (recommended combined claim direction)

D1. Dual-view mode decision: raw path for emergency immediacy + EMA path for stable control (with hysteresis/cooldown).
D2. Same-tick cumulative admission projection (memory/CPU/GPU budgets update after each accepted task in the same tick).
D3. Per-GPU affinity projection with bound/unbound split budgeting.
D4. Bottleneck-directed normalized dual-target preemption scoring (memory and GPU reclaimed together).
D5. Reason-aware adaptive retry in real-machine evidence loop (different actions for missing emergency vs insufficient completion).

Engineering inference:
- D1-D5 as an inseparable combination is the strongest non-trivial technical narrative.
- Single-point claims on D1 or D2 are vulnerable to obviousness attacks.

## 5. Risk Rating Update

- RS-P01 family (US20200167197A1 + US11656911B2): HIGH risk baseline.
- Filing strategy impact:
  1. Do not claim "preemptive termination" in isolation.
  2. Bind D1-D4 (and optionally D5 as dependent claim) in one independent method claim.
  3. Keep wording away from explicit SLT policy and "other cloud relocation" phrasing.

## 6. What This Closes and What Remains

Closed in this revision:
- ISSUE-55 core gap (independent-claim-level structured comparison) is now materially completed at engineering level.

Still required for legal filing readiness:
1. Patent counsel formal claim chart (verbatim legal structure).
2. Family-wide dependency check (continuations/divisionals that may broaden overlap).
3. CN-side equivalent claim comparison after CNIPA full-text retrieval.
