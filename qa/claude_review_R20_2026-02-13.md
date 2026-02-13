# Claude Deep Review — R20 (2026-02-13)

## 0. Review Scope

**Submitted**: R24–R27 self-audits (consolidated review of 4 Codex rounds since R19)
**Focus**:
- R24: 专利 v2 文档 + completed≥5 真机实验
- R25: RS-P01 claim-level v2 + CNIPA 检索日志
- R26: CN top-3 claim-level + legal-status appendix
- R27: 规范文档重写 (AGENTS.md, RUNBOOK.md, review_checklist.md, codex_prompt_template.md)

**Verdict**: **PASS**

---

## 1. Test Execution

```
> python -m unittest discover -s prototype/tests -p "test_*.py" -v
Ran 75 tests in 0.603s → OK
```

| 检查 | 状态 |
|------|------|
| 75/75 tests | PASS ✓ |
| R27 自审计声明 75/75 | 一致 ✓ |
| pycache 清理后首次通过 | ✓ |
| validate_scheduler_config.py | PASS ✓ |

---

## 2. R24 — 真机 completed≥5 证据验证

### 2.1 Adaptive Retry Trajectory (5 Attempts)

数据来源：`figures/real_baseline_eventful_R24_summary_2026-02-13.json`

| Attempt | bias | high/emer | reason | action | completed | emergency | preempted |
|---------|------|-----------|--------|--------|-----------|-----------|-----------|
| 1 | 0.0 | 76/82 | low_signal_dynamic | tighten_escalate | 8 | 0 | 0 |
| 2 | -4.0 | 67/72 | low_signal_dynamic | tighten_escalate | 8 | 0 | 0 |
| 3 | -8.0 | 58/62 | missing_emergency | tighten_escalate | 8 | 0 | 0 |
| 4 | -12.0 | 50/53 | insufficient_completion | relax_hold | 2 | 7 | 3 |
| 5 | -4.0 | 56/60 | satisfied | stop | **7** | **3** | **1** |

### 2.2 Bias Transition Math Verification

```
Attempt 1→2: update(0.0, "low_signal_dynamic") = max(-20, 0-4) = -4.0 ✓
Attempt 2→3: update(-4.0, "low_signal_dynamic") = max(-20, -4-4) = -8.0 ✓
Attempt 3→4: update(-8.0, "missing_emergency_signal") = max(-20, -8-4) = -12.0 ✓
Attempt 4→5: update(-12.0, "insufficient_completion") = min(20, -12+8) = -4.0 ✓
```

### 2.3 relax_and_hold 分支语义验证

```
Attempt 4 → Attempt 5:
  wall: 24.0 → 32.0 (extended by 8) ✓
  task_count: 11 → 11 (NOT escalated) ✓
  base_mem: 4000 → 4000 (NOT escalated) ✓
  bias: -12 → -4 (relaxed by +8) ✓
```

### 2.4 Evidence Strength vs R23

| 维度 | R23 (R19评审) | R24 (本轮) | 提升 |
|------|--------------|------------|------|
| attempts | 2 | **5** | 完整展现所有分支 |
| completed | 3 | **7** | 达成 completed≥5 目标 |
| emergency_ticks | 13 | 3 | 合理（更宽松最终阈值） |
| preempted | 2 | 1 | 合理 |
| failure branches seen | 1 (missing_emergency) | **3** (low_signal + missing_emergency + insufficient_completion) | 全覆盖 |
| wall extension | 未触发 | **触发** (24→32) | relax_and_hold 首次实证 |

**R24 证据意义**：首次在真机环境中观测到全部三种失败原因分支及其对应的自适应动作，5 次尝试后自动收敛到满足双目标（completed=7, emergency=3）的配置。这是自适应重试策略的最完整实证。

---

## 3. R25 — RS-P01 Claim-Level v2

### 3.1 质量评估

`prior_art/resource_scheduler_claim_level_RS-P01_v2_2026-02-13.md`:

| 检查项 | 状态 |
|--------|------|
| 独立权利要求要素化拆解 (Claim 1/16/18) | ✓ |
| 逐要素对照表（8 行覆盖 E1-E7 + C1） | ✓ |
| 每项有 URL 来源 | ✓ |
| 高风险区域明确标注 (E6/M6 preemptive termination = High) | ✓ |
| 差异化束 D1-D5 完整且与代码对应 | ✓ |
| 诚实标注：不以"已核验"掩盖未做的法律工作 | ✓ |

### 3.2 关键判断复核

- RS-P01 High 风险定级合理：E6/M6 preemptive termination 与我们的抢占逻辑有实质重叠
- D1-D5 差异化束（dual-view + same-tick projection + per-GPU affinity + normalized preemption + adaptive retry）作为不可分割组合主张，策略正确
- 明确指出单独主张 preemption 不安全 ✓

**ISSUE-55 状态更新**：工程级 claim-level 对比已完成，法律级 verbatim chart 仍需专利律师参与。降级为 Info。

---

## 4. R26 — CN Top-3 + Legal Status

### 4.1 CN Top-3 Claim-Level Chart

`prior_art/resource_scheduler_claim_level_CN_top3_2026-02-13.md`:

| 检查项 | 状态 |
|--------|------|
| CN-RS-01/04/06 三篇覆盖 | ✓ |
| 每篇有独立权利要求要素化 | ✓ |
| 每篇有 overlap vs differentiation 分析 | ✓ |
| 每篇有 URL 来源 | ✓ |
| 风险矩阵（4 维评估） | ✓ |
| 实操指导（independent claim 绑定组合） | ✓ |

### 4.2 CNIPA Search Log

`prior_art/resource_scheduler_cnipa_search_log_2026-02-13.md`:

| 检查项 | 状态 |
|--------|------|
| 检索入口 URL 给出 (3 个 CNIPA 链接) | ✓ |
| 关键词组记录 (4 组) | ✓ |
| 候选清单 (10 项 CN 专利，均有 URL) | ✓ |
| 已验证 vs 待验证明确分离 | ✓ |
| 诚实标注：使用 Google Patents 镜像而非 CNIPA 直接检索 | ✓ |

### 4.3 Legal Status Appendix

`prior_art/resource_scheduler_cnipa_legal_status_appendix_2026-02-13.md`:
- CN-RS-01: pending/publication ✓
- CN-RS-04: Active (granted) ✓
- CN-RS-06: Active (granted) ✓
- 风险排序正确：granted > pending ✓

### 4.4 Prior Art Index v2

`prior_art/resource_scheduler_prior_art_index_v2_2026-02-13.md`:
- 结构清晰：Core Risk Family → Platform Baselines → CN Candidates → Claim Strategy → Open Items
- 所有条目有 URL ✓
- Claim 策略指导与 RS-P01 v2 一致 ✓

**ISSUE-51 状态更新**：CNIPA 检索已执行（10 项候选），top-3 claim-level 对比已完成，legal-status appendix 已归档。降级为 Info（剩余工作：正式 CNIPA 官方截图 + CNKI/Wanfang 非专利文献）。

---

## 5. R27 — 规范文档重写

### 5.1 AGENTS.md

| 检查项 | 状态 |
|--------|------|
| 角色边界（非决策者 + 重大变更提案制） | ✓ |
| 强制工作顺序 (spec → tests → prototype → figures → qa/logs) | ✓ |
| 编码规范（UTF-8 无 BOM + 类型注解 + 依赖白名单） | ✓ |
| 自审计 8 章节模板 + 5 关键规则 | ✓ |
| 10 条 Red Lines（含 ISSUE 引用） | ✓ |
| 双 LLM 协作流程图 + 3 原则 | ✓ |
| 完成定义 (DoD) | ✓ |

### 5.2 RUNBOOK.md

| 检查项 | 状态 |
|--------|------|
| 验证三板斧（含 Step 0 pycache 清理） | ✓ |
| 真机命令完整 | ✓ |
| 提交安全规则（禁止 git add .） | ✓ |
| 常见故障处理 | ✓ |

### 5.3 review_checklist.md

| 检查项 | 状态 |
|--------|------|
| 28 项，6 大类 | ✓ |
| 新增：自审计检查（6 项） | ✓ |
| 新增：Spec 同步检查（4 项） | ✓ |
| 新增：安全检查（4 项） | ✓ |

### 5.4 codex_prompt_template.md

| 检查项 | 状态 |
|--------|------|
| System prompt 完整（角色 + 顺序 + 编码 + 验证 + Red Lines） | ✓ |
| 4 种任务模板 (A/B/C/D) | ✓ |
| 评审反馈修复模板 | ✓ |
| 使用示例（基于 R19 P1） | ✓ |

---

## 6. Findings

### ISSUE-63 (Info) — R25/R26 文件含 UTF-8 BOM

以下文件以 UTF-8 BOM (0xEF 0xBB 0xBF) 开头，违反 AGENTS.md §4.1 "无 BOM" 规则：
- `prior_art/resource_scheduler_claim_level_RS-P01_v2_2026-02-13.md`
- `prior_art/resource_scheduler_cnipa_search_log_2026-02-13.md` (无 BOM，clean ✓)
- `prior_art/resource_scheduler_claim_level_CN_top3_2026-02-13.md` (有 BOM)
- `prior_art/resource_scheduler_cnipa_legal_status_appendix_2026-02-13.md` (有 BOM)
- `prior_art/resource_scheduler_prior_art_index_v2_2026-02-13.md` (有 BOM)
- `qa/deep_algorithm_self_audit_R25_2026-02-13.md` (有 BOM)
- `qa/deep_algorithm_self_audit_R26_2026-02-13.md` (有 BOM)

不影响功能，但应在下轮清理。

### OBS-12 (Info) — R24 Attempt 4 blocked=518

Attempt 4 以极低阈值 (50/53) 运行导致 518 次准入拦截和仅 2 个完成任务。自适应系统正确识别并在 Attempt 5 放宽阈值，证明 relax_and_hold 分支工作正常。

---

## 7. Issue Status Update

| ID | Severity | 状态 | 说明 |
|----|----------|------|------|
| ISSUE-51 | Med→**Info** | NARROWED | CNIPA 检索已执行（10 CN 候选 + top-3 claim chart + legal status），剩余：官方截图 + CNKI/Wanfang |
| ISSUE-55 | Med→**Info** | NARROWED | RS-P01 工程级 claim-level 完成，剩余：法律级 verbatim chart |
| ISSUE-58 | Med | CLOSED | R21+R23+R24 三轮实证 |
| ISSUE-61 | Low | OPEN | CPU 阈值硬编码（可接受） |
| ISSUE-62 | Info | OPEN | data_model.md 编码损坏 |
| ISSUE-63 | Info | NEW | R25/R26 文件含 BOM |
| OBS-12 | Info | NEW | R24 Attempt 4 极端阈值下 blocked=518 |

---

## 8. Verified Fixes / Artifacts

| Fix/Artifact | 验证方式 |
|------|----------|
| F-46: R24 真机 completed=7 (≥5 target) | JSON 数据 + 5-attempt bias 数学追溯 ✓ |
| F-47: 自适应重试全 3 分支实证 | JSON trajectory: low_signal + missing_emergency + insufficient_completion 全覆盖 ✓ |
| F-48: relax_and_hold 分支首次实证 | wall 24→32, task/mem 不变, bias -12→-4 ✓ |
| F-49: RS-P01 claim-level v2 | 7 要素逐条覆盖 + D1-D5 差异化束 ✓ |
| F-50: CNIPA 检索日志 | 10 CN 候选 + URL + CPC 关键词 ✓ |
| F-51: CN top-3 claim-level chart | 3 篇独立权利要素化 + overlap/diff 分析 ✓ |
| F-52: Legal status appendix | 3 篇状态分类 (pending vs active) ✓ |
| F-53: Prior art index v2 | 22 条目 (3 RS-P01 + 9 platform + 10 CN) ✓ |
| F-54: Technique-claim mapping v2 | CP-1~CP-4 + CP-3A 全映射到代码/测试/证据 ✓ |
| F-55: AGENTS.md 重写 | 12 节完整规范 ✓ |
| F-56: RUNBOOK.md 重写 | 验证三板斧 + 故障处理 ✓ |
| F-57: review_checklist.md 扩展 | 28 项 6 类 ✓ |
| F-58: codex_prompt_template.md 新建 | 4 模板 + 修复模板 + 示例 ✓ |

---

## 9. Overall Assessment

**PASS** — R24-R27 四轮工作质量一致、证据充分、规范落地到位。

**核心成果**：

1. **R24 — 最强真机证据**：5 次自适应尝试覆盖全部 3 种失败分支，最终 completed=7 达成 ≥5 目标。首次实证 relax_and_hold 分支（wall 扩展 + 阈值放宽 + 负载不变）。
2. **R25/R26 — Prior Art 体系化**：RS-P01 + CN top-3 要素化对比，CNIPA 检索从零到 10 候选 + legal-status 归档。ISSUE-51/55 从 Med 降级为 Info。
3. **R27 — 规范工业化**：AGENTS.md（12 节）、RUNBOOK.md（故障处理）、review_checklist（28 项）、codex_prompt_template（4 模板）形成完整治理体系。

**当前项目健康度**：
- 代码：production-ready，75/75 tests，无已知 bug
- 真机证据：completed=7, 3 种自适应分支全覆盖
- Prior Art：22 条目索引 + 4 篇 claim-level 对比
- 治理规范：完整落地

---

## 10. Next Steps (R28+ 建议)

### P1 — CNKI/Wanfang 非专利文献（中优先级）
1. 至少 5 条可追溯学术文献条目
2. 与现有 prior_art index v2 合并
3. 关注"GPU 调度 + 准入控制"和"多资源抢占"方向的中文论文

### P2 — 清理 BOM 文件（低优先级）
1. ISSUE-63 涉及的 7 个文件去除 BOM
2. 可结合其他文档工作一并完成

### P3 — 可选增强
1. 修复 data_model.md 编码问题 (ISSUE-62)
2. 真机多轮 CI 统计（双目标达成率的置信区间）
3. 专利 v2 文档的 Claude 独立评审（单独一轮聚焦专利文本质量）

---

*Reviewed by Claude Opus 4.6 — 2026-02-13*
