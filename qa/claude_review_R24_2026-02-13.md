# Claude Review — R24 (2026-02-13)

## 0. Review Scope

**Codex 轮次**: R31 (Review-Repair + B-专利文档)
**审查对象**: 权利要求书 v3 + 说明书 v3 + 附图说明 v3 + ISSUE-64 修复
**Verdict**: **PASS — 4 个 Critical 缺陷全部修复，专利文本从 draft-level 升级到 filing-grade**

---

## 1. 测试确认

```
pycache 清理 → OK
python -m unittest discover -s prototype/tests -p "test_*.py"
Ran 75 tests in 0.632s → OK
```

调度器代码和测试未修改，75/75 基线不变。

---

## 2. Critical 缺陷逐项验证

### PATENT-ISSUE-1 (Critical) — 独立权利要求混入测试方法论 → **FIXED**

v2 独立权利要求 1 包含 7 个特征，其中第 6-7 项描述事件驱动真机重试（测试方法）。

v3 独立权利要求 1 现仅包含 5 个核心调度机制特征：
1. 周期采样
2. 双视图模式判定
3. 同周期累计准入投影（含 per-GPU 分桶）
4. 紧急阻断 + 归一化回收评分
5. 定向抢占 + 目标停止

自适应重试已**正确移入**从属权利要求 12-13，表述为产品能力（"自适应参数调优步骤"）而非测试方法。

### PATENT-ISSUE-2 (Critical) — 权利要求使用代码变量名 → **FIXED**

对 `patent/` 目录 v3 文件执行 grep 检查，以下变量名**零命中**：
`emergency_ticks`, `threshold_bias`, `low_signal_dynamic`, `task_count`, `duration_sec`, `base_mem_mb`, `ema_alpha`, `preempted_total`, `max_scheduler_wall_sec`, `adaptation_action`, `retry_reason`, `target_gpu_index`, `_can_admit`, `_preempt`, `resource_reclaim_score`

所有匹配项仅出现在 v1/v2 旧版文件中。v3 全部使用技术特征描述语言：
- `ema_alpha` → "平滑系数"
- `threshold_bias` → "准入阈值偏置量"
- `task_count` → "任务数量参数"
- `retry_reason` → "重试原因类别"

### PATENT-ISSUE-5 (Critical) — 说明书严重不足 → **FIXED**

| 指标 | v2 | v3 | 目标 |
|------|----|----|------|
| 行数 | 121 | 822 | 500-1000 ✓ |
| 摘要 | 无 | 有（~300 字） | 100-300 字 ✓ |
| 背景引证 | 0 | 6 项 | ≥5 ✓ |
| 发明内容三段式 | 无 | 有（§3.1/3.2/3.3） | ✓ |
| 实施例 | 0 | 5 个（§9.1-9.5） | ≥2-3 ✓ |
| 数值演算 | 无 | 有（§10，含具体数字） | ✓ |
| 对比表 | 无 | 有（§11.2，12 特征×6 系统） | ✓ |
| 附图详述 | 1 句/图 | 10 条/图 | ✓ |
| 参数配置表 | 无 | 3 组（§18.1-18.3） | ✓ |
| 权利要求支撑映射 | 无 | 有（§13.2 表格） | ✓ |
| 术语定义 | 无 | 有（§五） | ✓ |

### PATENT-ISSUE-6 (Critical) — 背景技术无具体引证 → **FIXED**

说明书 §2.2 现包含 6 项引证，每项均有：
1. 技术描述
2. 可核验来源 URL
3. 不足分析（与本发明的差异）

| 编号 | 引证来源 | URL 可核验 | 不足分析 |
|------|----------|-----------|----------|
| 2.2.1 | US20200167197A1 | ✓ | 缺少累计投影+per-GPU 分桶 |
| 2.2.2 | K8s Pod Priority | ✓ | 缺少 per-GPU 显存投影 |
| 2.2.3 | K8s Node-pressure Eviction | ✓ | 缺少归一化联合评分 |
| 2.2.4 | CN111736987B | ✓ | 仅 GPU 级微观调度 |
| 2.2.5 | Linux OOM Killer | ✓ | 仅内存单维评分 |
| 2.2.6 | Slurm Preemption | ✓ | 缺少完整组合机制 |

§2.3 综合不足归纳了 5 个系统性缺失，为发明内容提供了明确的问题导向。

---

## 3. High 缺陷验证

### PATENT-ISSUE-3 (High) — 独立权利要求特征过多 → **FIXED**

v2: 7 个特征（混合调度+测试）→ v3: 5 个特征（纯调度机制）。在 R21 建议的 4-5 个范围内。

### PATENT-ISSUE-4 (High) — 系统权利要求 15 过简 → **FIXED**

v2 claim 15 仅列模块名称。v3 claim 15 现包含 7 个子项，每个模块有：
- "用于..." 功能描述
- 输入/输出数据流连接
- 闭环声明语句

### ISSUE-64 (High) — CNKI 关键词编码损坏 → **FIXED (encoding)**

R30_targets.json 已修正为正确的 UTF-8 编码（`%E8%B5%84%E6%BA%90` 替代 `%3F%3F`）。重跑结果 ok=13 err=1（CNIPA 412 预期失败）。

**残留限制**（诚实记录）：CNKI 关键词页面仍返回相同 hash，因 CNKI 需要 JavaScript 执行/登录态。这不是编码问题，是环境限制，已如实标注。

### PATENT-ISSUE-7 (High) — Prior art 搜索方法缺陷 → **PARTIALLY ADDRESSED**

说明书背景引证已覆盖 Linux OOM Killer，但仍**缺少**：
- Gandiva (OSDI 2018)
- Tiresias (NSDI 2019)
- AntMan (OSDI 2020)
- Pollux (OSDI 2021)

这些是 claim-level prior art 分析的缺口，不影响说明书背景引证的合格性（说明书背景只需引用代表性现有技术），但**影响提交前的风险评估完整度**。

### PATENT-ISSUE-8 (High) — CN-RS-06 定性错误 → **NOT ADDRESSED**

CN116719628B 在 prior art 文档中仍被归入 CN 候选集。R21 指出该专利是数据传输链路调度（非计算资源调度），风险应降为 Low。本轮未修正。

---

## 4. 数值演算交叉验证

抽检 §10 数值演算的数学正确性：

**准入投影** (§10.2-10.3):
- 设备内存 8192 MB，80% 占用 = 6554 MB
- 任务 A +400 MB → 6954/8192 = **84.88%** ✓
- 任务 B +350 MB → 7304/8192 = **89.15%** ✓
- 任务 C +500 MB → 7804/8192 = **95.25%** > 92% → 阻断 ✓

**回收评分** (§10.5):
- 任务 D: mem=1000/900=1.11, gpu=1200/1100=1.09, synergy=1.11+1.09+min(1.11,1.09)=**3.29** ✓
- 任务 E: mem=1300/900=1.44, gpu=100/1100=0.09, synergy=1.44+0.09+min(1.44,0.09)=**1.62** ✓
- D > E → 优先回收双瓶颈任务 ✓

数值演算与代码实现一致（`resource_reclaim_score` at resource_scheduler.py:799-813）。

---

## 5. 权利要求-说明书支撑验证（抽检）

| 权利要求 | 声称支撑章节 | 实际验证 |
|----------|-------------|----------|
| Claim 1 (独立) | §7, §8, §9, §10 | ✓ 五个特征均有对应段落 |
| Claim 5 (per-GPU) | §7.4, §9.3 | ✓ 绑定/未绑定分桶描述完整 |
| Claim 8 (协同评分) | §8.4, §10.5 | ✓ 公式+数值示例均存在 |
| Claim 12 (参数调优) | §7.7, §9.4 | ✓ 分支策略描述完整 |
| Claim 15 (系统) | §6, §12 | ✓ 模块数据流对应 |

---

## 6. Issue Status Summary

| ID | Severity | 状态 | 说明 |
|----|----------|------|------|
| PATENT-ISSUE-1 | Critical | **CLOSED** | 独立权利要求纯调度机制 |
| PATENT-ISSUE-2 | Critical | **CLOSED** | 零代码变量名（grep 验证） |
| PATENT-ISSUE-3 | High | **CLOSED** | 5 特征（合理范围） |
| PATENT-ISSUE-4 | High | **CLOSED** | 系统权利要求含数据流 |
| PATENT-ISSUE-5 | Critical | **CLOSED** | 822 行，全部必要章节 |
| PATENT-ISSUE-6 | Critical | **CLOSED** | 6 项引证 + URL + 不足分析 |
| PATENT-ISSUE-7 | High | NARROWED | 说明书背景合格；claim-level Gandiva/AntMan 缺口仍存 |
| PATENT-ISSUE-8 | High | OPEN | CN-RS-06 定性未修正 |
| ISSUE-64 | High | **CLOSED** | 编码修复，环境限制诚实标注 |

---

## 7. 修正后授权概率评估

| 场景 | R21 估计 | R24 修正 | 变化原因 |
|------|---------|---------|----------|
| 当前文本直接提交 | 15-25% | **35-45%** | 4 Critical 全部修复，说明书从 3 页扩至 15+ 页 |
| 修复剩余 High 后 | 40-55% | **45-55%** | PATENT-ISSUE-7/8 影响降低 |
| + 专业代理人优化 | 55-70% | **60-70%** | 代理人可进一步优化权利要求层次和语言精度 |

**最大改善来自**：说明书扩写（+700 行）+ 背景引证补充（0→6 项）+ 独立权利要求聚焦。

---

## 8. 剩余改进建议（非阻塞）

1. **PATENT-ISSUE-7 残余**：补充 Gandiva/AntMan claim-level 对照（prior art 完整性），但不影响提交
2. **PATENT-ISSUE-8 残余**：在 prior art index 中将 CN-RS-06 降级为 Low 风险
3. **说明书微调**：§11.2 对比表中 Slurm 的"依实现而异"/"依策略脚本"可更具体
4. **摘要独立文件**：中国专利申请通常要求摘要单独成页，可从说明书中拆出
5. **IPC 分类建议**：可在说明书中补充 G06F 9/50（调度）或 G06F 9/48（任务管理）

---

## 9. Overall Assessment

**PASS** — R31 是本项目迄今**最重要的单轮改善**。

**修复质量**：
- 4 个 Critical 全部实质修复（非表面修改）
- 权利要求从 7→5 特征，去除测试方法，去除代码变量名
- 说明书从 121→822 行，覆盖摘要/背景引证/三段式/5 实施例/数值演算/对比表/附图详述/支撑映射
- 附图说明从 1 句/图→10 条/图
- 数值演算数学正确（交叉验证通过）

**Codex 自审计质量**：准确（无夸大），残留问题诚实标注。

**当前状态**：专利文本从 "NOT READY for filing" 升级为 **"filing-ready with recommended improvements"**。可以提交，但建议先由专利代理人做最终润色。

---

*Reviewed by Claude Opus 4.6 — 2026-02-13*
*本轮标志性转变：专利文本质量首次追上代码质量水平*
