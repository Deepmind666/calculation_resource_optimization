# Claude Review R14 — 2026-02-11

**Scope**: Codex R16 — P-04 混合场景升级, P-05 紧约束变体, 多种子置信区间, 真机基线框架
**Reviewer**: Claude Opus 4.6
**Verdict**: **PASS** — 实验严谨度显著提升; 多种子 CI 为专利证据提供统计学显著性

---

## 1  测试与验证

| 检查项 | 结果 |
|--------|------|
| `python -m unittest discover` | **60/60 PASS** (+7: 含 3 test_advanced_research.py 新测试) |
| `qa/validate_scheduler_config.py` | PASS |
| `prototype/run_experiments.py` | 4 场景 OK |
| `prototype/run_patent_evidence.py` | P-02 + P-03 OK |
| **多种子 CI 数学验证** | 手动验证 CI95 公式 ✓ (见 §4) |

**ISSUE-56 (Low): 自审报告测试数不一致**
自审报告声称 58/58 测试, 实际为 60/60。差异来源: 3 个 `test_advanced_research.py` 测试 (含新增的 `test_multiseed_confidence_summary_has_ci_bounds`), 且核心调度器测试在持续增加。轻微但应在自审中修正。

## 2  ISSUE 修复验证

| ID | 修复声明 | 验证 | 详情 |
|----|----------|------|------|
| ISSUE-52 | P-04 增加混合场景 | **YES** | 4 场景: other_card_only, same_card_only, mixed_cards, no_planned_budget |
| ISSUE-53 | P-05 增加紧约束变体 | **YES** | tight k=5, 恢复率分化: normalized 91.3%, raw 87.2%, random 89.9% |
| ISSUE-54 | P-05 恢复率分化 | **YES** | 紧约束下三策略恢复率不再全为 100% |

## 3  P-04 实验: 分层场景分析

### 数据一致性验证 ✓

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| 总试验数 | 20000 | 4967+5027+4997+5009 = 20000 | ✓ |
| 总安全案例 | 16222 | 4437+3534+3748+4503 = 16222 | ✓ |
| per_gpu_admit 求和 | 16222 | 4437+3534+3748+4503 = 16222 | ✓ |
| aggregate_admit 求和 | 13254 | 2768+3534+2449+4503 = 13254 | ✓ |
| aggregate_false_blocks 求和 | 2968 | 1669+0+1299+0 = 2968 | ✓ |

### 场景分布结果 (20,000 trials)

| 场景 | 试验数 | 安全率 | Aggregate FB | Per-GPU FB | 优势 |
|------|--------|--------|-------------|-----------|------|
| other_card_only | 4967 | 89.3% | **37.6%** | **0.0%** | -37.6pp |
| same_card_only | 5027 | 70.3% | 0.0% | 0.0% | 0pp (正确) |
| mixed_cards | 4997 | 75.0% | **34.7%** | **0.0%** | -34.7pp |
| no_planned_budget | 5009 | 89.9% | 0.0% | 0.0% | 0pp (正确) |
| **总计** | **20000** | **81.1%** | **18.3%** | **0.0%** | **-18.3pp** |

### 方法论评估

**优势**:
- same_card_only 和 no_planned_budget 两个场景中 per-GPU 和 aggregate 结果完全一致 (0% false-block) — 这是正确的:
  - same_card: 所有预算在目标卡上, 两种方法看到相同的信息
  - no_budget: 无额外预算, 两种方法等价
- mixed_cards 场景(34.7%)几乎与 other_card_only (37.6%)一样强 — 证明在混合负载下 per-GPU 的优势仍然显著
- 各场景试验数接近均匀 (4967~5027), 符合 `rng.choice` 等概率分布的预期采样方差

**ISSUE-52 状态**: **完全关闭** — 混合场景证据比单一极端场景更具说服力。

### 多种子 CI (7 seeds × 5000 trials)

| 指标 | 均值 | 95% CI | 标准差 |
|------|------|--------|--------|
| P-04 false_block_reduction | **18.64%** | [18.09%, 19.19%] | 0.74% |

**CI 下界 18.09% > 0** — 跨种子一致, 统计学显著。

## 4  P-05 实验: 归一化抢占评分

### 无限制模式 (preempt_limit=24)

| 策略 | 平均抢占次数 | 恢复率 | Normalized 胜率 |
|------|-------------|--------|-----------------|
| **Normalized** | **3.686** | 100% | — |
| Raw MB | 3.886 | 100% | 83.4% |
| Random | 3.864 | 100% | 82.5% |

Normalized 节省约 0.2 次抢占/试验 (vs raw), 约 5.1% 效率提升。

### 紧约束模式 (k=5)

| 策略 | 平均抢占次数 | 恢复率 | Normalized 胜率 |
|------|-------------|--------|-----------------|
| **Normalized** | **3.516** | **91.3%** | — |
| Raw MB | 3.646 | 87.2% | 84.9% |
| Random | 3.683 | 89.9% | 85.1% |

关键发现:
- **vs Raw**: +4.1pp 恢复率, -0.13 抢占次数 → **强证据**
- **vs Random**: +1.4pp 恢复率, -0.17 抢占次数 → **正面但边际较窄**

### 多种子 CI (7 seeds × 5000 trials)

| 指标 | 均值 | 95% CI | min/max |
|------|------|--------|---------|
| 恢复率优势 vs raw | **+3.66pp** | [+3.56, +3.76] | 3.5~3.9pp |
| 恢复率优势 vs random | **+1.25pp** | [+0.99, +1.51] | 0.9~1.8pp |
| Normalized 恢复率 | 90.86% | [90.47, 91.24] | 90.0~91.7% |
| Normalized 抢占次数 | 3.522 | [3.510, 3.535] | 3.50~3.54 |

### CI 数学验证

验证 `p05_tight_recovery_advantage_vs_random`:
- n=7, mean=0.012486, stddev=0.003487
- CI95_half = 1.96 × 0.003487 / √7 = 1.96 × 0.003487 / 2.646 = 0.002583
- CI = [0.012486 - 0.002583, 0.012486 + 0.002583] = **[0.009903, 0.015069]**
- CSV 记录: ci95_low=0.009903, ci95_high=0.015069 ✓ **完全吻合**

### 统计学意义

**CI 下界 +0.99pp > 0** — 归一化评分在 7 个独立种子中一致优于随机策略。即使用更保守的 t-分布 (df=6, t=2.447), CI 下界仍为 +0.92pp > 0。

**ISSUE-53/54 状态**: **关闭** — 紧约束变体成功展示恢复率分化, 多种子 CI 确认统计显著性。

### ISSUE-57 (Low): 自审 P-05 数据与 JSON 不一致

| 指标 | 自审声称 | JSON 实际 | 偏差 |
|------|---------|----------|------|
| normalized 恢复率 (tight) | 88.575% | **91.3%** | +2.7pp |
| normalized 抢占次数 (tight) | 3.5421 | **3.5164** | -0.026 |
| normalized 抢占次数 (full) | 3.7551 | **3.6864** | -0.069 |
| raw 恢复率 (tight) | 87.2% | 87.2% | 0 ✓ |
| random 恢复率 (tight) | 89.855% | 89.855% | 0 ✓ |

**分析**: 仅 normalized 策略数值不同, raw 和 random 完全一致。这说明在自审编写后, normalized 路径的代码或实验设置有变更。自审结论 "random still has slightly higher recovery" 在当前 JSON 数据中是**错误的** — normalized (91.3%) > random (89.9%)。

**影响**: 自审的消极结论实际上是过时的; 当前数据对 CP-2 是正面证据。

## 5  真机基线评估

### 数据状态

**真机基线数据未出现在当前 JSON 和 CSV 中**。CSV 由一次包含 `--multi-seed-runs 7` 但不含 `--run-real-baseline` 的运行生成。自审中记录了一次包含 `--run-real-baseline` 的运行, 但其输出未保留在制品中。

### ISSUE-58 (Medium): 真机基线设计缺陷

基于自审描述的参数:
- `base_mem_mb=96` — 每任务最大 1.8×96=173 MB, 6 并发约 1 GB — 在 16+ GB 机器上仅占 ~6% 内存, **远不足以触发 HIGH (85%) 或 EMERGENCY (92%) 模式**
- `psutil` 未安装 → peak_memory_pct = null, peak_swap_pct = null — **无法量化内存峰值**
- 自审记录: "所有模式均完成 24/24 任务, 0 错误" — **调度器未被激活**

**结论**: 真机基线在当前配置下**不提供专利证据价值**。要有效验证需要:
1. `base_mem_mb ≥ 2048` (确保 6 并发 ≈ 12+ GB, 接近 16 GB 机器的 85% 阈值)
2. 安装 `psutil` (`pip install psutil`)
3. 使用 GPU 密集任务 (当前 `estimated_gpu_mem_mb=0`)
4. 延长任务持续时间 (2 秒太短, 调度器 tick 间隔 0.1s 意味着仅 ~20 tick)

## 6  多种子 CI 框架评审

### 代码质量

`run_multiseed_confidence_summary` (lines 608-674) 实现清晰:
- 7 种子 × 5000 trials/种子, 使用素数步长 (9973) 避免种子相关性 ✓
- `_mean_ci95` (lines 590-605) 正确实现 CI95 = mean ± 1.96 × σ/√n ✓
- 测试 `test_multiseed_confidence_summary_has_ci_bounds` 验证 CI 界合理性 ✓

### OBS-01 (Info): CI 使用正态近似而非 t-分布

n=7 样本的 95% CI 应使用 t(df=6) 临界值 2.447, 而非正态 1.96。实际 CI 约窄 20%。但因所有 CI 下界均远离 0, 结论不受影响。未来可考虑使用 `scipy.stats.t.ppf(0.975, n-1)` 提升精度。

### OBS-02 (Info): JSON 与 CSV 不同步

JSON 不含 multiseed 数据 (由不含 `--multi-seed-runs` 的运行生成), 但 CSV 包含完整多种子 CI 行。建议统一用一次完整运行重生成两者:
```
python prototype/run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5 --multi-seed-runs 7 --multi-seed-trials 5000 --run-real-baseline --real-base-mem-mb 2048
```

## 7  专利证据强度评估

| 保护点 | 证据 | 统计显著性 | 强度 |
|--------|------|-----------|------|
| CP-1 per-GPU 亲和准入 | P-04: 18.6% 误阻塞消除, 4 场景 | CI95 [18.1%, 19.2%] | ★★★★★ |
| CP-2 归一化抢占评分 | P-05: +1.25pp vs random, +3.66pp vs raw | CI95 下界 > 0 | ★★★★☆ |
| CP-3 双视图+累积投影 | P-02: 0 vs 3 ticks 延迟; P-03: 2 vs 4 过量准入 | 单场景, 无 CI | ★★★☆☆ |

**CP-1 是最强证据点**, 应作为权利要求核心。CP-2 统计显著但绝对优势较窄。CP-3 需要类似 P-04/P-05 的多种子 CI 升级。

## 8  Issue 跟踪

| ID | 严重度 | 状态 | 描述 |
|----|--------|------|------|
| ISSUE-52 | Low | **CLOSED** | P-04 混合场景 — 4 场景类型, 数据一致 |
| ISSUE-53 | Medium | **CLOSED** | P-05 紧约束变体 — k=5 恢复率分化, 多种子 CI 确认 |
| ISSUE-54 | Low | **CLOSED** | P-05 恢复率 100% → 紧约束下 87~91% 分化 |
| ISSUE-56 | Low | NEW | 自审测试数 58 vs 实际 60 |
| ISSUE-57 | Medium | NEW | 自审 P-05 normalized 数据过时 — 声称 88.6% < random 89.9%, 实际 91.3% > 89.9% |
| ISSUE-58 | Medium | NEW | 真机基线无效 — base_mem_mb=96 太小, psutil 缺失, 调度器未被激活 |
| ISSUE-51 | Medium | OPEN | CNIPA 搜索计划但未执行 |
| ISSUE-55 | Medium | OPEN | RS-P01 对比停留在特征级, 非逐条权利要求 |

## 9  Verdict

**PASS** — R16 是迄今最严谨的实验轮次。关键成就:

1. **多种子 CI 分析** (新增) — 7×5000=35000 trials, 所有指标 CI 下界 > 0, 这是专利证据质量的飞跃
2. **P-04 4 场景分层** — 完全回应 ISSUE-52, mixed_cards (34.7%) 证明非极端场景下仍有显著优势
3. **P-05 紧约束** — k=5 条件下恢复率分化, normalized 一致优于 raw 和 random
4. **测试覆盖** — 60/60, 含多种子 CI 测试

## 10  下一步 (优先级排序)

### P1: 修复当前问题

1. **ISSUE-57**: 更新自审 P-05 数据为 JSON 实际值, 删除 "random has higher recovery" 结论
2. **OBS-02**: 统一运行一次完整命令重生成 JSON+CSV, 确保两者一致:
   ```
   python prototype/run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5 \
     --multi-seed-runs 7 --multi-seed-trials 5000
   ```

### P2: 真机基线重设计 (ISSUE-58)

3. **安装 psutil**: `pip install psutil`
4. **提高内存压力**: `--real-base-mem-mb 2048 --real-task-count 12 --real-fixed-workers 6`
   - 目标: 6×2048×1.8=22 GB 并发, 在 32 GB 机器上触发 ~69% 内存; 需要更多并发或更大任务
   - 或: `--real-base-mem-mb 3072 --real-task-count 8 --real-fixed-workers 8` → 8×3072×1.8=44 GB → 会触发 EMERGENCY
5. **如有 GPU**: 增加 `estimated_gpu_mem_mb > 0` 的任务类型

### P3: CP-3 证据补强

6. **P-02/P-03 多种子 CI**: 将 `run_patent_evidence.py` 的 P-02/P-03 扩展为多种子模式, 使 CP-3 达到与 CP-1/CP-2 同等的证据标准
7. 或: 将 P-02/P-03 整合进 `run_advanced_research.py` 的多种子框架

### P4: 专利深化 (持续)

8. **RS-P01 逐条权利要求分析** (ISSUE-55) — 下载 US11656911B2 授权版权利要求原文
9. **CNIPA 搜索执行** (ISSUE-51)
10. **说明书引用多种子 CI 数据** — 将 CI 区间写入有益效果章节

---

### 关于 "估算自校准" 提案

同意自审观点: 这是独立特性, 不应混入当前 3 点发明。建议先提交当前专利, 自校准作为后续改进或从属权利要求。
