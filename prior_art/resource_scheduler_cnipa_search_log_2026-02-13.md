# CNIPA-Oriented Prior-Art Search Log (Resource Scheduler)

- Timestamp: 2026-02-13 14:35:00 +08:00
- Owner: Codex (GPT-5)
- Review targets: ISSUE-51 (CNIPA search missing), ISSUE-47 follow-up
- Scope: Resource scheduling / admission / preemption / GPU-aware control

## 1. Search Entry Points

Official CNIPA entry pages:
1. https://pss-system.cponline.cnipa.gov.cn/conventionalSearch
2. https://www.cnipa.gov.cn/art/2023/2/13/art_3166_182074.html
3. https://www.cnipa.gov.cn/art/2024/4/1/art_3359_191346.html

Mirror used for machine-readable extraction and sharing:
- Google Patents (CN publication pages)

Rationale:
- CNIPA web interface is JS-heavy and not automation-friendly in this tooling context.
- Candidate identification and metadata extraction were done from public CN patent pages on Google Patents, then aligned to CNIPA search scope.

## 2. Query Set (executed)

CPC focus:
- G06F9/50 (resource allocation / scheduling)
- G06F11/34 (monitoring / fault handling)

Keyword groups:
1. "GPU 任务 调度 抢占 资源 分配"
2. "算力 资源 调度 admission preemption"
3. "site:patents.google.com CN G06F9/50 GPU 调度"
4. "CN GPU virtualization task scheduling memory"

## 3. Candidate Results (CN scope)

| ID | Patent | URL | Relevance to our project | Initial risk |
|---|---|---|---|---|
| CN-RS-01 | CN117788264A - GPU virtualization method | https://patents.google.com/patent/CN117788264A/en | GPU virtual resource assignment by memory demand + task scheduling component | Medium |
| CN-RS-02 | CN114968601A - AI training job scheduling with proportional reserved resources | https://patents.google.com/patent/CN114968601A/zh | Resource reservation + training-job scheduling | Medium |
| CN-RS-03 | CN111913794B - Methods/devices for shared GPU | https://patents.google.com/patent/CN111913794B/zh | Shared-GPU management and allocation paths | Medium |
| CN-RS-04 | CN111736987B - Task scheduling based on GPU space sharing | https://patents.google.com/patent/CN111736987B/zh | GPU-space sharing + scheduling behavior | Medium |
| CN-RS-05 | CN118672767B - GPU virtualization + AI compute scheduling | https://patents.google.com/patent/CN118672767B/zh | Scheduling with time-slice + priority + optimization | Medium |
| CN-RS-06 | CN116719628B - Preemptive scheduling for concurrent tasks | https://patents.google.com/patent/CN116719628B/zh | Direct preemptive scheduling relevance | Medium-High |
| CN-RS-07 | CN116860391A - GPU compute-resource scheduling method | https://patents.google.com/patent/CN116860391A/zh | VM-to-GPU selection and passthrough scheduling | Medium |
| CN-RS-08 | CN118502939B - Computing-power resource allocation method | https://patents.google.com/patent/CN118502939B/zh | General compute-power resource allocation | Low-Medium |
| CN-RS-09 | CN118132267A - Server GPU power integration/config/allocation | https://patents.google.com/patent/CN118132267A/zh | GPU resource integration and allocation system | Medium |
| CN-RS-10 | CN116089077A - GPU cluster resource scheduling | https://patents.google.com/patent/CN116089077A/zh | Cluster-side GPU scheduling and dispatch | Medium |

## 4. What Is Already Verified vs Pending

Verified in this round:
1. CN candidates exist with valid publication pages and metadata URLs.
2. Candidate set expanded beyond previous 3-item narrow scope.
3. CPC-relevant examples (including explicit G06F9/50 classification on CN118672767B page) were captured.

Pending (must be done before legal filing):
1. Full-text claim-by-claim chart for top CN candidates (at least CN-RS-01, CN-RS-04, CN-RS-06).
2. Legal-status cross-check directly in CNIPA and/or official legal-status services.
3. Chinese academic literature pass (CNKI/Wanfang) for non-patent prior art.

## 5. Engineering Impact on Claim Strategy

Practical implication for our filing draft:
1. Keep our independent claim centered on integrated combination (dual-view mode + same-tick cumulative projection + per-GPU affinity budgeting + bottleneck-directed dual-target preemption).
2. Treat preemption-only or GPU-allocation-only claim language as high-risk for novelty/obviousness.
3. Continue tightening wording around normalization-based multi-resource scoring and bound/unbound GPU budget split.

## 6. Closure Status

- ISSUE-51: materially improved (CN-oriented search evidence now documented), not legally final-closed yet.
- Exit criteria to fully close ISSUE-51:
  1. 3+ CN patents with claim-level element charts.
  2. CNIPA-side legal-status snapshots archived.
  3. Non-patent Chinese literature references added.
