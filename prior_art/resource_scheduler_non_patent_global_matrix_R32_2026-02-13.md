# Resource Scheduler Non-Patent Global Matrix (R32)

- Timestamp: 2026-02-13 20:36:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: close English-literature coverage gap raised in patent review (PATENT-ISSUE-7 follow-up)
- Scope: GPU/cluster scheduler baselines and kernel-level resource-pressure controls

## 1. Coverage Matrix

| ID | Source | Venue/Type | URL | Relevance | Overlap Summary | Risk |
|---|---|---|---|---|---|---|
| NP-G01 | Gandiva: Introspective Cluster Scheduling for Deep Learning | OSDI 2018 | https://www.usenix.org/conference/osdi18/presentation/xiao | High | GPU cluster scheduling, time-slicing and job migration logic | Medium-High |
| NP-G02 | Tiresias: A GPU Cluster Manager for Distributed DL | NSDI 2019 | https://www.usenix.org/conference/nsdi19/presentation/gu | High | Priority-aware GPU scheduling and fairness controls | Medium |
| NP-G03 | AntMan: Dynamic Scaling on Shared GPUs | OSDI 2020 | https://www.usenix.org/conference/osdi20/presentation/xiao | High | Fine-grained GPU sharing and adaptive resource use | Medium |
| NP-G04 | Pollux: Co-Adaptive Cluster Scheduling for DL | OSDI 2021 | https://www.usenix.org/conference/osdi21/presentation/qiao | High | Online adaptation and resource-efficiency optimization | Medium |
| NP-G05 | Linux OOM Handling | Kernel documentation | https://docs.kernel.org/mm/oom.html | High | Pressure-triggered victim scoring and process termination | Medium |
| NP-G06 | Linux PSI | Kernel documentation | https://docs.kernel.org/accounting/psi.html | Medium-High | Pressure signal abstraction and saturation detection | Medium |
| NP-G07 | NVIDIA MIG User Guide | Vendor technical documentation | https://docs.nvidia.com/datacenter/tesla/mig-user-guide/ | Medium-High | Device partitioning/isolation for GPU resources | Medium |
| NP-G08 | NVIDIA MPS Documentation | Vendor technical documentation | https://docs.nvidia.com/deploy/mps/index.html | Medium | GPU process sharing and multiplexing model | Low-Medium |
| NP-G09 | Hadoop YARN CapacityScheduler | Framework documentation | https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/CapacityScheduler.html | Medium | Queue-level admission and preemption policy baseline | Medium |
| NP-G10 | Kubernetes Dynamic Resource Allocation | Framework documentation | https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/ | Medium | Device-aware assignment baseline for admission | Medium |

## 2. Gap-to-Claim View

Current claim backbone (engineering perspective):
1. Dual-view mode decision (raw emergency + smoothed stable path).
2. Same-tick cumulative admission projection.
3. Per-GPU bound/unbound split budgeting.
4. Bottleneck-directed normalized dual-target reclaim.

Directly closest baselines from this matrix:
1. NP-G01 / NP-G02 / NP-G03 / NP-G04 on GPU scheduler adaptation.
2. NP-G05 on pressure-triggered victim scoring.
3. NP-G07 / NP-G08 on device-level GPU control.

Differentiation still maintained at combined-mechanism level:
1. Per-GPU bound/unbound cumulative admission projection in same tick.
2. Raw-emergency + smoothed-stable dual-view mode controller with cooldown+hysteresis.
3. Normalized dual-resource reclaim with dual-goal stop condition.

## 3. Practical Risk Notes

1. Single feature novelty is weak against this global matrix.
2. Combination claim strategy remains mandatory.
3. NP-G05 (Linux OOM) is the strongest conceptual overlap for victim-scoring logic; wording should avoid broad single-score claims.
4. NP-G01~G04 raise obviousness pressure for generic “adaptive GPU scheduling”; claims should anchor to combined admission-projection + bottleneck reclaim loop.

## 4. Follow-up Actions

1. Add legal-grade claim chart linking independent claim elements against NP-G01~G05.
2. Keep CN and global non-patent references in a unified claim-risk appendix.
3. Prefer claim language that binds all three core protection points as one indivisible loop.
