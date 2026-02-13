# Resource Scheduler Claim-Level Comparison with English Literature (2026-02-13)

- Timestamp: 2026-02-13 20:44:00 +08:00
- Owner: Codex (GPT-5)
- Task type: D-前置检索
- Purpose:
  1. close PATENT-ISSUE-7 narrowed gap with claim-level English literature comparison;
  2. provide reviewer-ready risk classification for Gandiva and Linux OOM killer.

## 1. Source Set (primary references)

1. Gandiva (OSDI 2018, USENIX page with abstract text):  
   https://www.usenix.org/conference/osdi18/presentation/xiao
2. Linux kernel source (`oom_badness` implementation):  
   https://raw.githubusercontent.com/torvalds/linux/master/mm/oom_kill.c
3. Linux OOM score adjustment man page:  
   https://www.man7.org/linux/man-pages/man5/proc_pid_oom_score_adj.5.html
4. Optional extension:
   - AntMan (OSDI 2020): https://www.usenix.org/conference/osdi20/presentation/xiao
   - Pollux (OSDI 2021): https://www.usenix.org/conference/osdi21/presentation/qiao

## 2. Claim Baseline (independent method claim, 5 features)

Baseline file: `patent/权利要求书_资源调度_v3.md`

Feature extraction from claim 1 (lines 9-13):

1. F1: Periodic multi-resource sampling (CPU/memory/GPU) and raw snapshot construction.
2. F2: Dual-view mode decision:
   - emergency uses raw sampling;
   - stable mode uses smoothed sampling.
3. F3: Non-emergency admission with same-tick cumulative projection, including:
   - per-GPU bucketed budget;
   - unbound-task conservative budget.
4. F4: Emergency branch blocks new admissions, identifies bottleneck/hot GPU, and computes normalized reclaim score from memory-gap and GPU-gap contributions.
5. F5: Directed preemption ordered by priority + score + task order, stopping when emergency reclaim target is met.

Implementation anchor of normalized scoring:
`prototype/resource_scheduler.py:799-813`

## 3. Gandiva (OSDI 2018) Claim-Level Mapping

### 3.1 Abstract summary (from source)

From USENIX abstract page:
Gandiva introduces introspective scheduling for deep-learning GPU clusters, using intra-job predictability to time-slice GPUs, migrate jobs, and improve utilization/latency.

### 3.2 Feature-by-feature mapping

| Claim feature | Gandiva coverage | Evidence-based note | Risk |
|---|---|---|---|
| F1 multi-resource periodic sampling | Partial | Gandiva is introspective and tracks job behavior for placement/migration, but focus is DL-job/GPU behavior rather than host CPU-memory-GPU unified safety snapshot. | Low-Medium |
| F2 raw-emergency + smoothed-stable dual-view mode | No direct match | Gandiva source describes introspection, time-slicing, and migration; no explicit dual-view emergency controller with raw vs smoothed decision split. | Low |
| F3 same-tick cumulative admission projection with per-GPU bound/unbound split | No direct match | Gandiva is cluster scheduling/time-slicing oriented; no explicit same-tick cumulative admission budget loop or bound/unbound conservative projection in claim core. | Low |
| F4 emergency block + bottleneck/hot-GPU + normalized gap-based reclaim score | Partial | Gandiva supports job prioritization/kill in feedback-driven exploration context, but not explicit normalized reclaim scoring by memory/gpu gaps with hot-GPU targeting. | Medium |
| F5 directed preemption with explicit reclaim-target stop | Partial | Gandiva has migration/time-slicing and job-level controls; no explicit dual-resource reclaim-stop criterion in claim statement. | Medium |

### 3.3 Gandiva overall conclusion

1. Overall risk: Medium.
2. Main overlap:
   - GPU scheduling optimization and dynamic control logic.
3. Main differences:
   - Gandiva is cluster performance scheduler;
   - our claim is node-level safety controller with admission-projection + emergency reclaim closed loop.
4. Differentiation conclusion:
   - single-feature novelty is weak;
   - combined mechanism (F2+F3+F4+F5) remains the key defensible path.

## 4. Linux OOM Killer (`oom_badness`) Difference Analysis

### 4.1 Primary code evidence

From `mm/oom_kill.c` (`oom_badness`):

1. Function intent:
   - “return the highest value for the task consuming the most memory”.
2. Score baseline:
   - `points = rss + swapents + page tables`.
3. Adjustment:
   - `points += oom_score_adj * totalpages/1000`.

This is a memory-centric victim-selection heuristic.

### 4.2 Mapping to our normalized reclaim scoring

| Dimension | Linux `oom_badness` | Our normalized reclaim scoring | Difference conclusion |
|---|---|---|---|
| Resource dimensions | Memory-only core | Memory + GPU dual-dimension | OOM lacks GPU reclaim semantics |
| Normalization basis | process memory footprint + `oom_score_adj` scaling | contribution divided by current reclaim gaps (`mem_denom`, `gpu_denom`) | OOM not gap-target normalized |
| Synergy term | None | `mem_unit + gpu_unit + min(mem_unit, gpu_unit)` in dual emergency | Our model explicitly rewards dual-bottleneck relief |
| Admission linkage | None | coupled with same-tick admission projection loop | OOM is reactive kill path, no proactive admission control |
| Stop rule | choose victim by highest badness in OOM flow | stop when reclaim target(s) reached | Our stop condition is explicit dual-goal control |

### 4.3 Risk grading for normalized-score claim point

1. Risk for F4 (scoring idea overlap): Medium.
2. Risk for full independent-claim 5-feature combination: Low-Medium.
3. Differentiation conclusion:
   - Linux OOM supports “score-based victim selection” prior art pressure;
   - does not cover our dual-resource gap-normalized + admission-coupled + target-stop closed loop.

## 5. Optional Extensions (AntMan / Pollux)

### 5.1 AntMan (OSDI 2020)

1. Focus:
   - dynamic GPU memory/compute scaling and co-execution in production clusters.
2. Overlap:
   - adaptive GPU scheduling and utilization optimization.
3. Missing vs claim 1:
   - no explicit raw-vs-smoothed emergency mode split;
   - no same-tick cumulative admission projection with bound/unbound GPU budget in claim core.
4. Risk: Medium.
5. Differentiation conclusion:
   - overlaps on adaptive GPU management, not full node-level safety closed loop.

### 5.2 Pollux (OSDI 2021)

1. Focus:
   - co-adaptive scheduling and goodput optimization.
2. Overlap:
   - online adaptive resource assignment under fairness constraints.
3. Missing vs claim 1:
   - no explicit emergency branch with normalized dual-resource reclaim scoring;
   - no explicit same-tick cumulative admission budget in claimed form.
4. Risk: Medium.
5. Differentiation conclusion:
   - strong optimization baseline but not equivalent to our emergency safety controller pipeline.

## 6. Consolidated Risk Summary

| Item | Focus | Overall risk | Key differentiation conclusion |
|---|---|---|---|
| Gandiva (OSDI 2018) | GPU cluster scheduling | Medium | lacks explicit dual-view emergency + same-tick projection + normalized dual-target reclaim loop |
| Linux OOM `oom_badness` | memory victim scoring | Medium (for F4), Low-Medium (for full 5-feature claim) | memory-only reactive scoring, no per-GPU admission/reclaim coupling |
| AntMan (OSDI 2020, optional) | dynamic GPU scaling | Medium | lacks claim-1 closed-loop safety composition |
| Pollux (OSDI 2021, optional) | co-adaptive goodput scheduling | Medium | optimization-centric, not explicit emergency reclaim controller |

## 7. Practical Filing Guidance

1. Keep independent claim bound to the inseparable 5-feature loop (F1-F5), not a single scoring idea.
2. Avoid over-broad wording that can be mapped to generic score-based victim selection.
3. Emphasize:
   - same-tick cumulative projection,
   - per-GPU bound/unbound budgeting,
   - dual-resource gap-normalized reclaim with explicit stop target.
