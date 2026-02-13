# Claude Review R15 — 2026-02-11

**Scope**: Codex R17 (双紧急协同评分) + R18 (多种子 CI 框架)
**Reviewer**: Claude Opus 4.6
**Verdict**: **PASS** — R17 的协同评分是 CP-2 证据从"弱"到"强"的关键转折点

---

## 1  测试与验证

| 检查项 | 结果 |
|--------|------|
| `python -m unittest discover` | **60/60 PASS** |
| `qa/validate_scheduler_config.py` | PASS |
| `prototype/run_experiments.py` | PASS |
| `prototype/run_patent_evidence.py` | PASS |
| Algorithm pseudocode 一致性 | `algorithm_pseudocode.md:337-347` 与 `resource_scheduler.py:795-809` 完全匹配 ✓ |

## 2  R17 算法变更：深度审查

### 2.1  公式变更概述

**修改位置**: `resource_scheduler.py:795-809`, `resource_reclaim_score()` 内部

| 条件 | 旧公式 (R11~R16) | 新公式 (R17+) |
|------|-------------------|---------------|
| 仅 memory 紧急 | `mem_norm` | `mem_norm` (不变) |
| 仅 GPU 紧急 | `gpu_norm` | `gpu_norm` (不变) |
| **双维紧急** | `mem_norm + gpu_norm` | `mem_unit + gpu_unit + min(mem_unit, gpu_unit)` |

其中 `mem_unit = min(1.0, mem_norm)`, `gpu_unit = min(1.0, gpu_norm)`

### 2.2  数学验证 — 新测试场景

**test_mixed_emergency_prefers_dual_reclaim_contributor** (line 1156):

| 参数 | 值 |
|------|-----|
| memory 使用率 | 85% (= memory_emergency_pct → 紧急) |
| GPU card[0] | 97% (>= 95% → 紧急) |
| reclaim_needed_mem | 8500 - (10000×80% - 512) = **1012 MB** |
| reclaim_needed_gpu | 9700 - (10000×85%) = **1200 MB** |

| 任务 | mem_norm | gpu_norm | 旧 score | 新 score | 胜者变化 |
|------|----------|----------|---------|---------|---------|
| MEM-HEAVY (1400/0) | 1.383 | 0 | **1.383** | 1.0+0+0 = **1.0** | 旧胜 |
| DUAL-BALANCED (600/700) | 0.593 | 0.583 | **1.176** | 0.593+0.583+0.583 = **1.759** | 新胜 |

- **旧公式**: 抢占 MEM-HEAVY → 1400 MB mem 回收 (138% 目标), 0 MB GPU 回收
- **新公式**: 抢占 DUAL-BALANCED → 600 MB mem (59%) + 700 MB GPU (58%) → **两维度同时缓解**

验证结果: 新公式在 k=1 紧约束下使调度器选择"双维贡献者", 避免一侧回收过剩但另一侧完全未解决的低效局面。 ✓

### 2.3  向后兼容验证

已有测试 `test_mixed_emergency_preempt_score_uses_normalized_resources` (line 1095):

| 任务 | 旧 score | 新 score | 排序 |
|------|---------|---------|------|
| MIXED-BALANCED | 2.073 | 1.511 | 1st (两种公式均如此) |
| MEM-HEAVY | 1.112 | 1.182 | 2nd |

排序不变 → 测试通过, 向后兼容 ✓

### 2.4  公式性质分析

```
score(a, b) = min(1, a) + min(1, b) + min(min(1, a), min(1, b))
```

| 性质 | 验证 |
|------|------|
| 值域 | [0, 3] (双满时 1+1+1=3) |
| 对称性 | score(a, b) = score(b, a) ✓ |
| 单侧封顶 | mem=2.0, gpu=0 → 1+0+0 = 1.0 (不因单侧溢出而偏高) |
| 协同激励 | mem=0.6, gpu=0.6 → 0.6+0.6+0.6 = 1.8 (> 1.0 的单侧) |
| 极端平衡 | mem=1.0, gpu=1.0 → 1+1+1 = 3.0 (最高分, 奖励理想回收者) |

**结论**: 公式合理, 本质上是 `sum + overlap` 模式, 类似 Choquet 容量的对偶: 既不忽略单侧贡献, 又额外奖励多维协同。

### 2.5  关键发现 — R17 是 P-05 数据翻转的根因

| 代码版本 | normalized 紧约束恢复率 | vs random 优势 |
|----------|------------------------|---------------|
| 旧公式 (R16 自审) | 88.6% | **-1.3pp** (输给 random) |
| 新公式 (R17) | 91.3% | **+1.4pp** (赢过 random) |

**这完全解释了 R14 评审中标记的 ISSUE-57**。R16 自审的数据并非"过时", 而是记录了旧公式的正确结果。R17 的协同评分使 normalized 策略在紧约束下的恢复率提升了 +2.7pp, 从输于 random 翻转为赢过 random。

**ISSUE-57 状态变更**: 从 "自审数据过时 → 需修正" 改为 "R17 算法改进的预期行为 → 已解释"。自审数据无需修正, 但建议在 R17 自审中补充说明此因果关系。

## 3  R18 多种子 CI 框架

### 已在 R14 评审中完整覆盖

R18 的 `_mean_ci95` + `run_multiseed_confidence_summary` + 测试 + CLI 参数已在 R14 评审中通过数学验证 (CI95 手算吻合) 和代码审查。此处不重复。

### 补充确认

| 项目 | R14 验证 | R15 复查 |
|------|---------|---------|
| CI 公式正确性 | ✓ 手算验证 | ✓ 一致 |
| 测试覆盖 | ✓ 3/3 pass | ✓ 60/60 pass |
| JSON + CSV 同步 | ⚠ R14 时不同步 | ✓ 现已同步 (JSON 18:43 含 multiseed 块) |
| 种子步长素数选择 | ✓ 9973 避免相关性 | ✓ 一致 |

## 4  Issue 跟踪

| ID | 严重度 | 状态变更 | 详情 |
|----|--------|---------|------|
| ISSUE-57 | Med → **Info** | **RECLASSIFIED** | 非数据过时, 而是 R17 公式改进的预期效果。自审 R16 数据是旧公式的正确记录。 |
| ISSUE-56 | Low | OPEN | 自审测试数 58→59→60, 应以最新代码为准 |
| ISSUE-58 | Med | OPEN | 真机基线设计缺陷未变 |
| ISSUE-51 | Med | OPEN | CNIPA 搜索未执行 |
| ISSUE-55 | Med | OPEN | RS-P01 逐条权利要求未完成 |

### 新观察

**OBS-03 (Info): 协同评分系数不可配置**

当前 `min(1.0, ...)` 封顶和 `1×` 协同加权是硬编码的。对于不同负载分布, 最优系数可能不同。当前作为合理默认值可接受, 但未来可考虑暴露为配置项 (如 `synergy_bonus_weight: 1.0`, `reclaim_cap: 1.0`)。

**OBS-04 (Info): P-05 simulation baseline 未更新协同评分**

P-05 的 `_simulate_preemption_baseline` 中 raw_mb 和 random 策略使用简单 `mem + gpu` 或随机值, 未反映协同评分。这是正确的 — 它们是对照基线, 不应使用被测算法。但 `_run_normalized_scheduler_trial` 通过调用真实 `_preempt_low_priority` 方法自动获得了 R17 的协同评分, 这是 normalized 策略恢复率提升的直接原因。

## 5  专利影响评估

### R17 对权利要求的影响

R17 的协同评分公式应当体现在专利文件中:

| 文档 | 当前状态 | 建议 |
|------|---------|------|
| `algorithm_pseudocode.md` | ✓ 已更新 (line 337-347) | OK |
| `权利要求书` claim 1 step 6 | 已有 "归一化回收评分" | **应明确"双维协同加分"** |
| `说明书` Section 五 | 有抢占评分描述 | **应增加混合紧急协同评分的具体公式和实例** |

### 证据强度变化

| 保护点 | R14 评估 | R15 评估 | 变化原因 |
|--------|---------|---------|---------|
| CP-1 per-GPU 亲和 | ★★★★★ | ★★★★★ | 不变 |
| CP-2 归一化抢占 | ★★★★☆ | **★★★★½** | R17 协同评分使 vs random 翻正; 多种子 CI 确认 |
| CP-3 双视图+累积 | ★★★☆☆ | ★★★☆☆ | 不变, 仍需多种子 CI |

## 6  Verdict

**PASS** — R17 + R18 是完整的"算法改进 → 量化验证 → 统计确认"闭环。

**R17 亮点**:
1. 协同评分公式动机清晰、数学合理、测试完备
2. 直接导致 normalized 策略在紧约束下从输于 random 翻转为赢过 random (+2.7pp 恢复率提升)
3. 对单维紧急场景无影响 (代码路径独立), 向后兼容
4. 伪代码文档同步更新

**R18 亮点**:
5. 多种子 CI 框架在 R14 已验证, JSON 现已包含完整 multiseed 数据
6. 60/60 测试, 所有回归脚本通过

## 7  下一步

### P1: 专利文件更新
1. **权利要求书 Claim 1 Step 6**: 增加"混合紧急时采用单维封顶加双维协同加分的评分策略"
2. **说明书**: 增加 R17 协同评分公式、数值实例、与旧公式的对比数据 (88.6% → 91.3%)

### P2: 持续优先 (从 R14)
3. **真机基线重设计** (ISSUE-58): base_mem_mb≥2048, 安装 psutil
4. **CP-3 多种子 CI**: 将 P-02/P-03 扩展为多种子模式
5. **RS-P01 逐条权利要求** (ISSUE-55)
6. **CNIPA 搜索** (ISSUE-51)
