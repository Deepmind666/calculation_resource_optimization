# CN Top-3 Claim-Level Comparison (Engineering Chart)

- Timestamp: 2026-02-13 15:20:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: close the claim-level gap for CN candidates (ISSUE-51 follow-up)
- Scope: CN-RS-01 / CN-RS-04 / CN-RS-06
- R32 correction note (2026-02-13): CN116719628B risk reclassified from Medium to Low due to domain mismatch (data-link scheduling vs compute-resource scheduling).

## 1. Source List (public URLs)

1. CN117788264A: https://patents.google.com/patent/CN117788264A/en
2. CN111736987B: https://patents.google.com/patent/CN111736987B/zh
3. CN116719628B: https://patents.google.com/patent/CN116719628B/zh

Reference anchors captured on 2026-02-13:
- CN117788264A: claim section around lines 277-287, legal status lines 17-18.
- CN111736987B: claim section around lines 310-333, legal status lines 17-18.
- CN116719628B: claim section around lines 437-483, legal status lines 17-18.

## 2. Comparison Baseline (our current scheduler)

Implementation references:
1. `prototype/resource_scheduler.py`
2. `prototype/run_advanced_research.py`
3. `prototype/tests/test_resource_scheduler.py`

Current differentiators we aim to protect:
1. Dual-view decision (raw emergency + EMA stable control).
2. Same-tick cumulative admission projection.
3. Per-GPU affinity projection with bound/unbound split.
4. Bottleneck-directed normalized dual-target preemption.

## 3. CN-RS-01: CN117788264A (GPU virtualization method)

### 3.1 Independent claim abstraction (method)

A1. Load a preconfigured interception library in container group.
A2. Intercept image-processing instruction from application.
A3. Decide resource allocation using rule/threshold.
A4. Forward accepted instruction to host scheduling component.
A5. Allocate virtual GPU resources according to memory demand and return result.

### 3.2 Overlap vs our project

1. Overlap:
   - Resource-allocation decision before execution.
   - GPU-memory-demand-aware assignment.
2. Main differences:
   - CN-RS-01 is interception + virtualization pipeline centric.
   - Our project is host-level admission/preemption safety scheduler (CPU+mem+GPU), not GPU API interception framework.
   - Our claim core includes same-tick cumulative projection + mode hysteresis + normalized dual-target reclaim.

### 3.3 Risk rating

- Risk: Medium.
- Reason: GPU allocation relevance is real, but system architecture and control objective differ significantly.

## 4. CN-RS-04: CN111736987B (GPU space-sharing task scheduling)

### 4.1 Independent claim abstraction

B1. Build GPU execution-state model to support preemption and space sharing.
B2. Use persistent-thread style processing and state-probability estimation.
B3. Evaluate IPC under candidate allocation plans.
B4. Use runtime scheduler to search evaluation table for resource decisions.
B5. Task scheduling path includes dynamic adjustment and preemption under deadline constraints.

### 4.2 Overlap vs our project

1. Overlap:
   - GPU preemption and dynamic scheduling under pressure.
2. Main differences:
   - CN-RS-04 is GPU micro-level performance-model scheduler (IPC/Markov/deadline modeling).
   - Our system is multi-resource host safety scheduler with admission blocking and emergency reclaim goals.
   - We do not implement Markov-IPC table search as core decision kernel.

### 4.3 Risk rating

- Risk: Medium-High.
- Reason: stronger scheduling and preemption overlap than CN-RS-01, despite different decision model.

## 5. CN-RS-06: CN116719628B (data-link concurrent scheduling)

### 5.1 Independent claim abstraction

C1. Classify data into transferable subtasks.
C2. Match subtasks to links/channels and build concurrent transfer plan.
C3. Compute link-state deviation rate vs threshold.
C4. If deviation exceeds threshold, priority-sort subtasks in same link.
C5. Otherwise execute concurrent transfers; optionally rebalance by link load.

### 5.2 Overlap vs our project

1. Overlap:
   - Threshold-triggered priority/preemption strategy.
   - Dynamic dispatch based on runtime state.
2. Main differences:
   - CN-RS-06 focuses on transmission-link scheduling (network/data pipeline).
   - Our project focuses on compute-resource admission and reclaim (memory/GPU/CPU) on host.
   - No per-GPU affinity budget split in CN-RS-06 claim core.

### 5.3 Risk rating

- Risk: Low.
- Reason: despite threshold and priority language overlap, the independent-claim core focuses on transmission-link task dispatch/rebalancing, not host-side CPU/memory/GPU admission + emergency reclaim.

## 6. Consolidated Risk Matrix

| Candidate | Domain similarity | Mechanism overlap | Differentiation strength | Overall risk |
|---|---|---|---|---|
| CN117788264A | Medium | Medium | High | Medium |
| CN111736987B | High | Medium-High | Medium | Medium-High |
| CN116719628B | Low | Low | High | Low |

## 7. Practical Filing Guidance

1. Keep independent claim bound to integrated combination (dual-view + same-tick projection + per-GPU split + normalized dual-target preemption).
2. Avoid standalone novelty statement on "preemption" or "GPU allocation".
3. Add dependent claims to explicitly include normalized scoring and bound/unbound GPU budget handling.

## 8. Remaining Gaps

1. This chart is engineering-level, not legal claim construction.
2. Need counsel-reviewed legal claim chart for top CN candidates before filing.
3. Need official legal-status snapshots archived from CNIPA workflows.
