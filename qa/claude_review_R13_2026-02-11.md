# Claude Review R13 — 2026-02-11

**Scope**: Codex R14 — ISSUE-45~50 fixes, P-04/P-05 experiments, RS-P01 claim-level comparison, SVG figures
**Reviewer**: Claude Opus 4.6
**Verdict**: **PASS** — major progress on evidence depth; experiment methodology has room to sharpen

---

## 1  Test & Validation

| Check | Result |
|-------|--------|
| `python -m unittest discover` | **53/53 PASS** (+2 new: test_advanced_research.py) |
| `qa/validate_scheduler_config.py` | PASS |
| `prototype/run_experiments.py` | 4 scenarios OK |
| `prototype/run_patent_evidence.py` | P-02 + P-03 OK |
| `prototype/run_advanced_research.py --trials 200` | P-04 + P-05 OK, results reproducible |

## 2  Issue Fix Verification

| ID | Fix Claimed | Verified | Details |
|----|-------------|----------|---------|
| ISSUE-45 | RS-P01 risk → High | **YES** | Prior art index: RS-P01 + RS-P01-G marked **高**, RS-P08 (family) also added as **高**. Separate claim-level doc created. |
| ISSUE-46 | RS-P02 description corrected | **YES** | Now reads "GPU 虚拟化环境自适应 timeslice 调度，含 round-robin 与 preemption overhead 调整" |
| ISSUE-47 | Prior art scope expanded | **PARTIAL** | Expanded from 14→25 items (16 papers/docs + 9 patents). CNIPA search PATH recorded but actual search NOT executed. CNKI/万方 still missing. See ISSUE-51. |
| ISSUE-48 | Claim 1 step 6 add "归一化" | **YES** | Step 6 now reads "基于任务资源归一化回收评分执行定向抢占" |
| ISSUE-49 | 说明书 quantify 有益效果 | **YES** | Section 三(三) now cites P-02 (0 vs 3 ticks) and P-03 (2 vs 4 tasks, 90.89% vs 100.66%) |
| ISSUE-50 | 说明书 concrete parameters | **YES** | New Section 五(七) with 实施例 A: full config values + workflow description |

## 3  P-04 Experiment: Per-GPU Affinity Ablation

### Results (20,000 trials)

| Metric | Per-GPU | Aggregate | Delta |
|--------|---------|-----------|-------|
| False-block rate | **0.0%** | **35.09%** | -35.09pp |
| Safe cases admitted | 18899/18899 | 12267/18899 | +35% |

Reproducibility confirmed at 200 trials: 0.0% vs 34.4% (consistent within sampling variance).

### Methodology Assessment

**Strengths**:
- Oracle ground truth: directly computes `(target_used + task_gpu) / total_gpu_mb < 95%`
- Large sample size (20k) gives high confidence
- `AggregateGpuProjectionScheduler` is a clean controlled ablation via subclassing

**ISSUE-52 (Low): P-04 scenario always puts planned budget on OTHER card**

The test always sets `planned_extra_gpu_by_index = {1: same_tick_other_card}` with `target_gpu_index = 0`. This is the maximal-interference scenario — aggregate projection is guaranteed to be penalized by card-1's budget while per-GPU correctly ignores it.

A more balanced test would include mixed scenarios:
- (a) All planned budget on other card (current) — per-GPU advantage is maximal
- (b) Some planned budget on same card — per-GPU advantage narrows
- (c) No planned budget — both methods equivalent

The 0% false-block rate for per-GPU is mathematically trivial in scenario (a): the oracle and per-GPU check the same condition. Adding scenario (b) would demonstrate per-GPU's advantage in realistic mixed workloads.

**Bottom line**: The result is directionally correct and genuinely demonstrates the advantage. The 35% false-block elimination is strong evidence for CP-1. The methodological bias doesn't invalidate the claim but makes the magnitude look more dramatic than a mixed-scenario test would show.

## 4  P-05 Experiment: Normalized Preemption Ablation

### Results (20,000 trials)

| Strategy | Avg Preemptions | Recovery Rate | Better-or-equal vs Normalized |
|----------|-----------------|---------------|-------------------------------|
| **Normalized** | **3.755** | **100%** | — |
| Raw MB | 3.886 | 100% | Normalized wins 88.4% |
| Random | 3.864 | 100% | Normalized wins 78.9% |

### Methodology Assessment

**Strengths**:
- Three-way comparison: normalized vs raw-MB vs random
- Mixed emergency (92-94% mem + 97-99% GPU) — forces dual-resource scoring
- 24 candidate tasks with realistic resource distributions (3 task archetypes)
- `_run_normalized_scheduler_trial` uses actual `_preempt_low_priority` method (not simulation)

**ISSUE-53 (Medium): Preemption improvement margin is modest**

The normalized scoring saves ~0.13 preemptions/trial (3.76 vs 3.89). That's a ~3.4% improvement. While it wins 88.4% of trials, the absolute improvement is small.

Contributing factor: `preempt_limit = len(runtimes) = 24` — every candidate is reachable. With a tighter limit (3-5), the scoring quality would matter more because wrong victim selection means failing to meet recovery goals.

**Recommendation**: Add a `preempt_limit=5` variant to P-05. If normalized scoring achieves higher recovery rate than raw-MB and random under tight limits, that's a much stronger patent evidence point ("normalized scoring enables recovery with fewer permitted preemptions").

**ISSUE-54 (Low): All strategies achieve 100% recovery rate**

With `preempt_limit = 24` (all candidates reachable), every strategy eventually finds enough tasks to reclaim. The meaningful comparison is preemption COUNT, not recovery RATE. Under tighter limits, recovery rate divergence would strengthen the evidence.

## 5  RS-P01 Claim-Level Comparison

### Assessment

The document correctly identifies 5 core elements of RS-P01 and maps each to our system's corresponding feature. The differentiation points are accurate:

| RS-P01 Element | Our Differentiator |
|----------------|-------------------|
| Resource discovery → ResourceMonitor | We add raw/EMA dual-view for different decision layers |
| Pending detection → pending queue | We add same-tick cumulative projection budget |
| Preemptive strategy → _preempt_low_priority | We add bottleneck-directed + normalized + GPU hotspot |
| Terminate low-priority → _stop_task | We add stuck escape + dual-target recovery stop |
| Reschedule high-priority → tick readmission | We add per-GPU target card + unbound conservative split |

### ISSUE-55 (Medium): Not yet a true claim-by-claim analysis

The current document extracts "核心要素" from the patent abstract, not from verbatim independent claims. A real claim-level analysis for patent defense should:
1. Quote each independent claim of US11656911B2 (granted version) verbatim
2. Map each claim element phrase to our system's corresponding feature or "NOT PRESENT"
3. Identify which elements in our Claim 1 are NOT covered by any RS-P01 claim
4. This is the "claim chart" format patent attorneys use for freedom-to-operate analysis

The current analysis is at "feature comparison" level, which is useful but not sufficient for a patent attorney to assess novelty. The "下一步" section correctly identifies this gap.

## 6  SVG Patent Figures

| Figure | Content | Assessment |
|--------|---------|------------|
| 图1 系统模块图 | 6 modules (监控, 判定, 准入, 回收, 执行, 审计) with connections | Functional, matches 说明书 and 权利要求 11. Basic SVG — adequate for draft, will need professional redrawing for submission. |
| 图2 调度周期流程图 | Tick lifecycle: snapshot → mode decision → emergency/normal paths → events | Captures the dual-path logic with cumulative projection annotation. Same quality note. |

Missing: 图3 (per-GPU budget/affinity) and 图4 (preemption scoring + dual-target recovery) — these are described in 说明书 Section 四 but not yet drawn.

## 7  Prior Art Index Quality

Expanded from 14 to 25 items:
- 16 papers/docs (RS-001 through RS-016) — all with URLs, most verified
- 9 patent candidates (RS-P01 through RS-P08 + RS-P01-G family member)
- 3 marked **High** risk (RS-P01, RS-P01-G, RS-P08 — same family)
- 6 marked Medium, 6 marked Low
- 5 new academic papers: Sparrow, Apollo, Medea, Firmament, Affinity-aware provisioning

### ISSUE-51 (Medium): CNIPA search recorded but NOT executed

Section 3 of the prior art index records CNIPA URLs and search plan but the actual search has not been performed. The 2 Chinese patents added (RS-P04 CN114968601A, RS-P05 CN117788264A) were found via Google Patents, not CNIPA. A proper CNIPA search with CPC G06F9/50 filtering is still needed before filing.

## 8  Issue Tracker

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| ISSUE-45 | High | **CLOSED** | RS-P01 risk upgraded to High + claim-level doc |
| ISSUE-46 | Medium | **CLOSED** | RS-P02 description corrected |
| ISSUE-47 | Medium | **PARTIALLY CLOSED** | Expanded to 25 items + CNIPA path, but actual search not executed |
| ISSUE-48 | Medium | **CLOSED** | Claim 1 step 6 now has "归一化" |
| ISSUE-49 | Low | **CLOSED** | 说明书 有益效果 quantified |
| ISSUE-50 | Low | **CLOSED** | 说明书 concrete parameter example added |
| ISSUE-51 | Medium | NEW | CNIPA search planned but not executed; CNKI/万方 still missing |
| ISSUE-52 | Low | NEW | P-04 scenario only tests max-interference case (all budget on other card) |
| ISSUE-53 | Medium | NEW | P-05 improvement margin modest (~3.4%); add tight preempt_limit variant |
| ISSUE-54 | Low | NEW | P-05 all strategies 100% recovery — need tighter limit to show rate divergence |
| ISSUE-55 | Medium | NEW | RS-P01 comparison is feature-level, not verbatim claim-level |

## 9  Verdict

**PASS** — This is the strongest evidence package so far. Key achievements:

1. **P-04 delivers compelling evidence for CP-1**: 35% false-block rate elimination is a clear quantifiable advantage
2. **P-05 provides directional evidence for CP-2**: normalized scoring wins in 88% of trials
3. **ISSUE-45~50 all addressed**: 4 fully closed, 1 partially closed (ISSUE-47), 1 closed (ISSUE-50)
4. **Prior art doubled**: 14 → 25 items with improved breadth
5. **SVG figures started**: adequate for draft stage
6. **Real machine baseline framework ready**: code exists and was smoke-tested

## 10  Next Steps (Prioritized)

### P1: Strengthen Evidence (use your compute)

1. **P-05 tight-limit variant**: Run with `preempt_limit=5` instead of 24. If normalized scoring achieves higher recovery rate under tight limits, that's the killer evidence for CP-2.

2. **P-04 mixed-scenario**: Add trials where planned budget is on SAME card as target. This tests a more realistic scenario and if per-GPU still has 0% false blocks with some same-card budget, the result is more convincing.

3. **Real machine baseline**: Run `--run-real-baseline` with higher task count and real memory pressure. Compare peak memory % across A/B/C conditions.

### P2: RS-P01 Deep Comparison

4. **Verbatim claim chart**: Download US11656911B2 granted claims (not just abstract). Quote each independent claim element. Map to our features. This is what a patent attorney needs.

5. **Minimum novel feature set**: After verbatim comparison, identify the SMALLEST combination of our features that is NOT covered by any RS-P01 claim. This becomes the core of the independent claim defense.

### P3: Search Completion

6. **Execute CNIPA search**: Actually run the CPC G06F9/50 query on the CNIPA system and export results
7. **CNKI/万方 academic search**: At least check for Chinese papers on GPU affinity scheduling and emergency preemption

### P4: Draft Refinement

8. **Draw figures 3 and 4**: per-GPU budget diagram and preemption scoring flow
9. **V2 权利要求书**: After RS-P01 verbatim comparison, rewrite Claim 1 to explicitly avoid RS-P01 coverage

---

### About the "估算自校准" proposal

The user's suggestion to "用历史运行结果回写 estimated_mem_mb/estimated_gpu_mem_mb" is interesting but I'd caution: this adds significant algorithmic complexity and is a NEW feature, not a bug fix or evidence improvement. It should NOT be mixed into the patent filing for the current 3 core protection points. If implemented, it could become a separate dependent claim or a future patent.

**Recommendation**: File the current 3-point invention first, then iterate on estimation self-calibration as an enhancement.
