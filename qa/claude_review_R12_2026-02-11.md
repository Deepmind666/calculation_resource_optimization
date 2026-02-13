# Claude Review R12 — 2026-02-11

**Scope**: Codex R13 — prior art rebuild + patent drafts + route decision + technique mapping
**Reviewer**: Claude Opus 4.6
**Verdict**: **Conditional PASS** — prior art framework is a major ISSUE-13 improvement, but 3 medium issues block patent submission readiness

---

## 1  Test Execution

| Check | Result |
|-------|--------|
| `python -m unittest discover` | **51/51 PASS** |
| `qa/validate_scheduler_config.py` | PASS |
| `prototype/run_experiments.py` | 4 scenarios OK |
| `prototype/run_patent_evidence.py` | P-02 + P-03 OK |

No algorithm code changes in R13 — all green as expected.

## 2  Document Inventory

| Document | Path | Assessed |
|----------|------|----------|
| Prior art search plan | `prior_art/resource_scheduler_search_plan.md` | ✓ |
| Prior art index (14 items) | `prior_art/resource_scheduler_prior_art_index.md` | ✓ |
| Claim chart (3 CPs) | `prior_art/resource_scheduler_claim_chart.md` | ✓ |
| 权利要求书 v1 (14 claims) | `patent/权利要求书_资源调度_v1.md` | ✓ |
| 说明书 v1 (7 sections) | `patent/说明书_资源调度_v1.md` | ✓ |
| Route decision report | `qa/patent_route_decision_report_2026-02-11.md` | ✓ |
| Technique-claim mapping v1 | `qa/technique_claim_mapping_resource_scheduler_v1_2026-02-11.md` | ✓ |
| Self-audit R13 | `qa/deep_algorithm_self_audit_R13_2026-02-11.md` | ✓ |
| prior_art/README.md | Updated — distinguishes old vs new direction | ✓ |
| patent/README.md | Updated — distinguishes old vs new direction | ✓ |

## 3  ISSUE-13 Assessment (Prior Art Fake Verification)

**Original problem**: 16 prior art items marked "已核验" with zero evidence.

**R13 resolution**:
- New index has 11 open-source/paper items + 3 patent candidates = 14 total
- All 11 have real, fetchable URLs
- 3 patent candidates honestly marked "待全文核验" (not "已核验")
- Each item has: 来源/URL, 主要披露点, 重叠点, 差异点, 风险级别, 状态

**Independent URL verification** (Claude):
- 3 Kubernetes URLs directly fetched and disclosure points confirmed word-for-word
- 3 patents fetched from Google Patents — titles and abstracts verified
- Remaining 3 (Slurm, PSI, cgroup v2) are canonical kernel/HPC doc URLs, content consistent with known documentation

**Verdict on ISSUE-13**: **PARTIALLY RESOLVED** — structure is now honest and traceable. Full resolution requires claim-level patent comparison (see ISSUE-46).

## 4  Prior Art Quality — Critical Findings

### ISSUE-45 (High): RS-P01 risk level underestimated

US20200167197A1 actual title: *"Systems, methods, and apparatuses for implementing a scheduler with preemptive termination of existing workloads to free resources for high priority items"*

This patent is **directly** about preemptive resource-aware scheduling:
- Has a "compute resource discovery engine" that monitors resources
- Can terminate lower-priority workloads to free capacity for higher-priority items
- Uses Service Level Targets (SLTs) for preemption decisions

**This overlaps significantly with CP-2 (bottleneck preemption)**. The risk should be **High, not Medium**. Claim-level comparison with CP-2 is urgently needed to understand differentiation (our per-GPU affinity weights, normalized scoring, dual reclaim targets may still be novel, but this must be verified).

### ISSUE-46 (Medium): RS-P02 description inaccurate

Prior art index describes RS-P02 as "云环境资源自适应分配" and asks "需核验是否涉及 device-aware admission".

Actual patent (US20230385093A1): *"Adaptive task scheduling for virtualized environments"* — about **GPU timeslice scheduling** in virtualized environments using round-robin with adaptive timeslice duration.

This is:
- More GPU-specific than described (it's about GPU compute time allocation, not general cloud resource allocation)
- About GPU **compute** timeslicing, not GPU **memory** admission control
- Uses round-robin scheduling (not priority-based preemption)

The description should be corrected. Risk level Medium is appropriate but for different reasons than stated.

### ISSUE-47 (Medium): Prior art search scope too narrow

Current search:
- 5 Kubernetes docs, 2 Linux kernel docs, 2 HPC docs, 2 papers, 3 patent candidates
- **No CNIPA (中国国家知识产权局) patent search** — mandatory before filing a Chinese 发明专利
- **No Chinese academic papers** (e.g., CNKI/万方)
- **No academic search beyond Borg/Omega** — missing key papers like Sparrow (2013), Apollo (2014), Medea (2017), Firmament (2016) that address GPU-aware or resource-fair scheduling
- **Only 3 patent candidates**, all at title-level — need 8-12 with claim-level comparison
- CPC `G06F9/50` search not actually executed (only listed as strategy)

**Impact**: The claim chart's "新颖性风险: 中" assessment cannot be trusted until proper patent search is done. The risk could be higher than estimated.

## 5  Patent Claims Assessment

### 权利要求书 Structure

| Type | Count | Assessment |
|------|-------|------------|
| Independent method claim (Claim 1) | 1 | Correctly binds CP-1 + CP-2 + CP-3 |
| Dependent method claims (2-10) | 9 | Good granularity |
| Independent system claim (11) | 1 | Standard mirror |
| Dependent system claims (12-13) | 2 | OK |
| Storage medium claim (14) | 1 | Standard |

### Strengths
1. **Claim 1 correctly uses combination strategy** — all 3 core points in one independent claim, not split
2. **Terminology consistent with code** — "双视图", "累计投影", "per-GPU 亲和", "定向抢占" all match
3. **Dependent claims drill into specifics** — EMA alpha, affinity weights, dual-target stop, stuck escape
4. **Claims 9-10 add practical features** — stuck task escape, blocked event observability

### ISSUE-48 (Medium): Claim 1 step 6 omits "归一化" (normalization)

Step 6 says: "基于任务资源回收评分执行定向抢占"

This misses the key ISSUE-37 fix: **normalized** scoring divides each resource contribution by its own reclaim gap. This normalization is the core differentiation that makes multi-resource preemption work correctly. Without it, MB units from different resources get mixed.

**Fix**: Step 6 should say "基于任务资源**归一化**回收评分执行定向抢占" or add normalization as a required characteristic of the independent claim.

### ISSUE-49 (Low): 说明书 "有益效果" lacks quantification

Section 三(三) claims:
- "零延迟识别紧急状态" → should cite P-02: 0 ticks vs 3 ticks delay
- "显著降低同周期超发风险" → should cite P-03: 2/4 tasks (50% reduction), 90.89% vs 100.66% peak

The numbers exist in the experiment data but aren't directly referenced in the 有益效果 section. Patent examiners prefer concrete quantified effects.

### ISSUE-50 (Low): 说明书 缺少具体参数实施例

Section 五 describes the algorithm but never gives concrete configuration values. A real implementation example should include at least:
- `memory_emergency_pct = 92%`, `ema_alpha = 0.6`, `memory_high_pct = 85%`
- `gpu_memory_emergency_pct = 95%`, `preempt_count_per_tick = 1`
- Specific task submission scenario with numbers

### OBS-10 (Info): 附图仅有草案

Section 四 describes 4 figures but none are drawn. Patent submission requires actual figures. This is expected at draft stage.

### OBS-11 (Info): 所有 R13 文档时间戳完全一致

All 6+ documents share timestamp `2026-02-11 13:03:10 +08:00`, indicating batch generation rather than sequential research. Not an issue per se, but worth noting.

## 6  Code-Claim Line Reference Verification

All line references in claim chart and technique mapping were independently checked against current `resource_scheduler.py`:

| Reference | Line Content | Match |
|-----------|-------------|-------|
| CP-1: `:496` | `_can_admit` method start | ✓ |
| CP-1: `:555` | `if task.target_gpu_index is not None:` | ✓ |
| CP-1: `:562` | `base_gpu_mb += float(per_gpu_budget.get(target, 0.0))` | ✓ |
| CP-1: `:564` | `base_gpu_mb += sum(float(v) for v in per_gpu_budget.values())` | ✓ |
| CP-2: `:694` | `_preempt_low_priority` method start | ✓ |
| CP-2: `:714` | hottest_gpu_index identification | ✓ |
| CP-2: `:747` | `effective_gpu_reclaim` function | ✓ |
| CP-2: `:791` | dual-target recovery check | ✓ |
| CP-3: `:432` | `_evaluate_mode` method start | ✓ |
| CP-3: `:440` | raw emergency comment | ✓ |
| CP-3: `:458` | cooldown logic | ✓ |
| CP-3: `:301` | `_can_admit` call with cumulative params | ✓ |
| CP-3: `:317` | `planned_extra_mem_mb += ...` cumulative update | ✓ |
| C8: `:656` | stop_failed handler | ✓ |
| C8: `:665` | stuck_task_timeout_sec check | ✓ |
| C8: `:675` | TASK_STUCK_REMOVED event | ✓ |
| C9: `:95` | `blocked_total` metrics field | ✓ |
| C9: `:817` | `blocked_total += 1` | ✓ |
| C9: `:820` | `blocked_task_total += 1` | ✓ |

Test references spot-checked:
- `:460` → `test_dry_run_admission_no_double_count_same_tick` ✓
- `:516` → `test_gpu_affinity_uses_target_card_projection` ✓
- `:1028` → `test_preempt_uses_raw_view_for_emergency_dimension_detection` ✓
- `:1094` → `test_mixed_emergency_preempt_score_uses_normalized_resources` ✓
- `:1428` → `test_real_run_projection_blocks_second_start_same_tick` ✓

**All 19 code + 5 test line references verified.** ✓

## 7  Route Decision Assessment

The route decision report recommends:
- **Primary**: Option B — complete claim-level patent comparison + real machine evidence before filing
- **Fallback**: Option C — 实用新型 if overlap is too high
- **Not recommended**: Option A — direct filing

**Assessment**: This is the correct call. The honest admission that "单点技术并不新" and the warning about insufficient claim-level comparison are appropriate. The two-week execution plan is realistic.

However, the plan underestimates one thing: with RS-P01 being directly about preemptive resource-aware scheduling (ISSUE-45), the risk may be higher than "中" across the board.

## 8  Issue Tracker

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| ISSUE-13 | High | **PARTIALLY RESOLVED** | Prior art index now has real URLs and honest status; claim-level comparison still needed |
| ISSUE-45 | **High** | **NEW** | RS-P01 (US20200167197A1) directly covers preemptive resource-aware scheduling — risk should be High not Medium |
| ISSUE-46 | Medium | NEW | RS-P02 description inaccurate — patent is about GPU timeslice scheduling, not general cloud allocation |
| ISSUE-47 | Medium | NEW | Prior art search too narrow — no CNIPA, no Chinese papers, only 3 patent candidates |
| ISSUE-48 | Medium | NEW | Claim 1 step 6 omits "归一化" — key normalization is core differentiator |
| ISSUE-49 | Low | NEW | 说明书 有益效果 lacks quantified P-02/P-03 numbers |
| ISSUE-50 | Low | NEW | 说明书 具体实施方式 lacks concrete parameter examples |
| OBS-10 | Info | NEW | 附图 only described, not drawn |
| OBS-11 | Info | NEW | All R13 documents share identical timestamp |

## 9  Improvement Recommendations (Prioritized)

### Priority 1: 专利检索补强 (blocks submission)

1. **RS-P01 claim-level comparison** — this is the #1 urgent task. Compare each of RS-P01's claims against our CP-1/CP-2/CP-3 and document differentiation
2. **CNIPA patent search** — search Chinese patent database for "资源调度 准入控制", "GPU 亲和调度", "紧急抢占回收" — required before filing in China
3. **Add 5-8 more patents** from CPC G06F9/50 and G06F11/34, with claim-level analysis
4. **Fix RS-P02 description** — "GPU 虚拟化环境自适应时间片调度" rather than "云环境资源自适应分配"

### Priority 2: 实验证据补强 (user has compute resources)

The user explicitly says "我本地的算力资源很强大，所以允许进行大规模实验". This is the opportunity to build real evidence:

5. **Real machine baseline experiment** — 3 conditions:
   - (A) No scheduler: submit all tasks immediately, measure peak memory/GPU, OOM count
   - (B) Fixed concurrency: `max_workers=4` with no admission control
   - (C) This scheduler: full `DynamicTaskScheduler` with production config
   - Metrics: peak memory %, peak GPU %, completion rate, OOM events, throughput, latency
   - Workload: mix of CPU-heavy, memory-heavy, GPU-heavy tasks with realistic estimates

6. **Per-GPU affinity ablation** (P-04 — new evidence point):
   - Compare: per-GPU projection vs aggregate-GPU-only projection
   - Setup: 2+ GPUs, tasks targeting specific cards
   - Metric: false-block rate (tasks blocked that would have fit on target card)
   - This directly supports CP-1's novelty claim

7. **Bottleneck-directed preemption ablation** (P-05 — new evidence point):
   - Compare: normalized scoring (current) vs raw-MB scoring (old) vs random preemption
   - Setup: mixed memory+GPU emergency scenario
   - Metric: reclaim efficiency (MB reclaimed per preemption), recovery ticks
   - This directly supports CP-2's novelty claim

### Priority 3: 文档完善

8. **Add "归一化" to Claim 1 step 6** — mention normalization in independent claim
9. **Quantify 有益效果** — cite P-02 (0 vs 3 ticks) and P-03 (2 vs 4 tasks, 90.89% vs 100.66%) directly
10. **Add concrete parameter example** to 说明书 Section 五
11. **Draw patent figures** — at least figures 1 (system modules) and 2 (tick cycle with cumulative projection)

## 10  Verdict

**Conditional PASS** — R13 delivers a well-structured prior art framework that substantially addresses ISSUE-13, with honest status labels, real URLs, and traceable evidence chains. The 权利要求书 correctly binds the 3 core protection points and the route decision is realistic.

**Conditions for full PASS**:
1. Fix ISSUE-45: upgrade RS-P01 risk to High and complete claim-level comparison
2. Fix ISSUE-46: correct RS-P02 description
3. Fix ISSUE-48: add "归一化" to Claim 1 independent claim

**Strong recommendation**: Before R14 proceeds to patent submission, complete the real machine baseline experiment (Priority 2 above). The user has compute resources. Synthetic ablation alone is insufficient to convince a patent examiner of "显著技术效果".
