# Resource Scheduler Prior-Art Index v2

- Timestamp: 2026-02-13 18:30:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: clean, review-ready index for current resource-scheduler direction

## 1. Core Risk Family (must-track)

| Family ID | Item | URL | Why it matters | Risk |
|---|---|---|---|---|
| RS-P01 | US20200167197A1 | https://patents.google.com/patent/US20200167197A1/en | Preemptive termination + resource-aware scheduling chain similar to our preemption loop | High |
| RS-P01-G | US11656911B2 | https://patents.google.com/patent/US11656911B2/en | Granted family member; independent claims overlap generic detect-overload-evict-reschedule flow | High |
| RS-P01-OLD | US10545796B2 | https://patents.google.com/patent/US10545796B2/en | Earlier family patent in similar direction | High |

## 2. Platform/Framework Baselines (non-patent)

| ID | Source | URL | Overlap summary | Risk |
|---|---|---|---|---|
| RS-001 | Kubernetes Pod Priority and Preemption | https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/ | Priority-based preemption | Medium |
| RS-002 | Kubernetes Node-pressure Eviction | https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/ | Pressure thresholds + eviction | Medium |
| RS-003 | Kubernetes ResourceQuota | https://kubernetes.io/docs/concepts/policy/resource-quotas/ | Admission control by quota | Medium |
| RS-004 | Kubernetes Dynamic Resource Allocation | https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/ | Device-aware resource assignment | Medium |
| RS-005 | Slurm Preemption | https://slurm.schedmd.com/preempt.html | Configurable preemption policies | Medium |
| RS-006 | Linux PSI | https://docs.kernel.org/accounting/psi.html | Resource pressure signals | Low-Medium |
| RS-007 | Linux cgroup v2 | https://docs.kernel.org/admin-guide/cgroup-v2.html | Memory control primitives (`memory.high`, `memory.max`) | Low-Medium |
| RS-008 | Borg (EuroSys 2015) | https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ | Cluster scheduling baseline | Low-Medium |
| RS-009 | Omega (EuroSys 2013) | https://research.google/pubs/pub41684 | Parallel scheduler architecture baseline | Low-Medium |

## 2.1 Global Scheduler Literature Extension (R32)

Detailed matrix:
1. `prior_art/resource_scheduler_non_patent_global_matrix_R32_2026-02-13.md`
2. `prior_art/resource_scheduler_claim_level_english_lit_2026-02-13.md`

Core additions:
1. Gandiva (OSDI 2018)
2. Tiresias (NSDI 2019)
3. AntMan (OSDI 2020)
4. Pollux (OSDI 2021)
5. Linux OOM / PSI
6. NVIDIA MIG / MPS
7. Hadoop YARN CapacityScheduler

Claim-level English literature chart:
1. `prior_art/resource_scheduler_claim_level_english_lit_2026-02-13.md`
2. Includes mandatory mapping for:
   - Gandiva vs independent claim-1 five features
   - Linux OOM `oom_badness` vs normalized reclaim scoring differences
3. Includes optional mapping for:
   - AntMan
   - Pollux

Element-level agent appendix:
1. `prior_art/resource_scheduler_claim_risk_appendix_R33_2026-02-13.md`
2. Covers independent claim-1 F1~F5 and dependent claim-7/8 with:
   - overlap evidence
   - defensible scope
   - wording avoidance suggestions

## 3. CN Candidate Set (expanded)

Detailed logs and archives:
1. `prior_art/resource_scheduler_cnipa_search_log_2026-02-13.md`
2. `prior_art/resource_scheduler_cnipa_legal_status_appendix_2026-02-13.md`
3. `prior_art/resource_scheduler_claim_level_CN_top3_2026-02-13.md`
4. `prior_art/resource_scheduler_cnipa_legal_status_archive_R28_2026-02-13.md`
5. `prior_art/resource_scheduler_non_patent_cnki_wanfang_matrix_R28_2026-02-13.md`
6. `prior_art/resource_scheduler_cnipa_cnki_snapshot_archive_R30_2026-02-13.md`
7. `prior_art/evidence/R30_snapshot_manifest.json`

Top CN candidates:
1. CN117788264A - https://patents.google.com/patent/CN117788264A/en
2. CN114968601A - https://patents.google.com/patent/CN114968601A/zh
3. CN111913794B - https://patents.google.com/patent/CN111913794B/zh
4. CN111736987B - https://patents.google.com/patent/CN111736987B/zh
5. CN118672767B - https://patents.google.com/patent/CN118672767B/zh
6. CN116719628B - https://patents.google.com/patent/CN116719628B/zh
7. CN116860391A - https://patents.google.com/patent/CN116860391A/zh
8. CN118502939B - https://patents.google.com/patent/CN118502939B/zh
9. CN118132267A - https://patents.google.com/patent/CN118132267A/zh
10. CN116089077A - https://patents.google.com/patent/CN116089077A/zh

CN-RS-06 correction:
1. `CN116719628B` has been reclassified as Low risk in `resource_scheduler_claim_level_CN_top3_2026-02-13.md` (R32 update), because independent-claim core is transmission-link scheduling rather than host compute resource admission/reclaim.

## 4. Claim Strategy Guidance (engineering view)

Recommended independent-claim backbone:
1. Dual-view mode decision (raw emergency + EMA stable control).
2. Same-tick cumulative admission projection.
3. Per-GPU affinity projection with bound/unbound split budgeting.
4. Bottleneck-directed normalized dual-target preemption.

Avoid claiming as stand-alone novelty points:
1. Generic three-mode state machine.
2. EMA smoothing by itself.
3. Preemption without integrated projection and affinity context.

## 5. Open Items Before Filing

1. RS-P01 formal legal claim chart by counsel.
2. CN claim-level charts for top 3 candidates (engineering draft done; legal version pending).
3. CNIPA official screenshot/export snapshots archived in filing-accepted format.
4. CNKI detailed result-page snapshot archive accepted by legal process.
5. Counsel-grade legal claim chart for global non-patent baselines (NP-G01~NP-G05).

## 6. Companion Documents

1. `prior_art/resource_scheduler_prior_art_package_R30_2026-02-13.md`
2. `prior_art/resource_scheduler_claim_level_RS-P01_v2_2026-02-13.md`
3. `prior_art/resource_scheduler_cnipa_search_log_2026-02-13.md`
4. `prior_art/resource_scheduler_claim_level_CN_top3_2026-02-13.md`
5. `prior_art/resource_scheduler_cnipa_legal_status_appendix_2026-02-13.md`
6. `prior_art/resource_scheduler_cnipa_legal_status_archive_R28_2026-02-13.md`
7. `prior_art/resource_scheduler_non_patent_cnki_wanfang_matrix_R28_2026-02-13.md`
8. `prior_art/resource_scheduler_cnipa_cnki_snapshot_archive_R30_2026-02-13.md`
9. `qa/technique_claim_mapping_resource_scheduler_v2_2026-02-13.md`
10. `prior_art/resource_scheduler_non_patent_global_matrix_R32_2026-02-13.md`
11. `prior_art/resource_scheduler_search_method_upgrade_R32_2026-02-13.md`
12. `prior_art/resource_scheduler_claim_level_english_lit_2026-02-13.md`
13. `prior_art/resource_scheduler_claim_risk_appendix_R33_2026-02-13.md`
