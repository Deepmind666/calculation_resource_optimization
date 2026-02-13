# Claude Review — R25 (2026-02-13)

## 0. Review Scope

**Codex 轮次**: R32 (D-前置检索 + PATENT-ISSUE-7/8 closure)
**审查对象**: English lit claim-level chart + CN-RS-06 reclassification + spec v3 Gandiva update + global matrix
**Verdict**: **PASS — PATENT-ISSUE-7 CLOSED, PATENT-ISSUE-8 CLOSED**

---

## 1. 测试确认

```
pycache 清理 → OK
Ran 75 tests in 0.495s → OK
```

代码基线不变。

---

## 2. PATENT-ISSUE-7 验证 — Prior art 搜索方法缺陷 → **CLOSED**

### 2.1 Claim-level 英文文献对照

`prior_art/resource_scheduler_claim_level_english_lit_2026-02-13.md` 逐特征对照覆盖：

| 文献 | 类型 | F1 采样 | F2 双视图 | F3 累计投影 | F4 归一化评分 | F5 定向抢占 | 总风险 |
|------|------|---------|----------|-----------|------------|-----------|--------|
| Gandiva (OSDI 2018) | GPU 集群调度 | Low-Med | Low | Low | Medium | Medium | **Medium** |
| Linux OOM `oom_badness` | 内存评分终止 | — | — | — | Medium | — | **Low-Medium** (全组合) |
| AntMan (OSDI 2020) | GPU 动态缩放 | — | — | — | — | — | **Medium** |
| Pollux (OSDI 2021) | 自适应吞吐调度 | — | — | — | — | — | **Medium** |

### 2.2 关键差异化结论（验证正确）

- **Gandiva**: 集群性能优化器，无节点级双视图紧急控制 + 无同周期累计投影 + 无 per-GPU bound/unbound 分桶
- **Linux OOM**: 纯内存单维反应式评分，无 GPU 维度、无 gap-normalized 双目标、无准入耦合
- **组合防御**: 5 特征组合（F1-F5）在逐文献对照中均无完全对应

### 2.3 说明书 v3 已同步更新

说明书 §2.2.7 新增 Gandiva/Tiresias/AntMan/Pollux 引证（含 4 个 USENIX URL + 差异分析）。
引证清单 §十七 新增第 7-10 项。
说明书从 821 行扩至 847 行。

### 2.4 全球非专利矩阵

`prior_art/resource_scheduler_non_patent_global_matrix_R32_2026-02-13.md` 新增 10 项全球文献覆盖（含 NVIDIA MIG/MPS、YARN CapacityScheduler 等）。

R21 §4.2 列出的所有缺失文献现已覆盖：
- [x] Gandiva (OSDI 2018)
- [x] Tiresias (NSDI 2019)
- [x] AntMan (OSDI 2020)
- [x] Pollux (OSDI 2021)
- [x] Linux OOM Killer
- [x] NVIDIA MIG/MPS
- [x] YARN CapacityScheduler

---

## 3. PATENT-ISSUE-8 验证 — CN-RS-06 定性错误 → **CLOSED**

Prior art index §3 现包含明确修正：
> "CN116719628B has been reclassified as Low risk ... because independent-claim core is transmission-link scheduling rather than host compute resource admission/reclaim."

CN top-3 claim-level 文档和 README 均已同步标注 R32 correction。

---

## 4. Issue Status Summary (Final)

| ID | Severity | 状态 | 关闭轮次 |
|----|----------|------|----------|
| PATENT-ISSUE-1 | Critical | **CLOSED** | R24 (R31) |
| PATENT-ISSUE-2 | Critical | **CLOSED** | R24 (R31) |
| PATENT-ISSUE-3 | High | **CLOSED** | R24 (R31) |
| PATENT-ISSUE-4 | High | **CLOSED** | R24 (R31) |
| PATENT-ISSUE-5 | Critical | **CLOSED** | R24 (R31) |
| PATENT-ISSUE-6 | Critical | **CLOSED** | R24 (R31) |
| PATENT-ISSUE-7 | High | **CLOSED** | R25 (R32) |
| PATENT-ISSUE-8 | High | **CLOSED** | R25 (R32) |
| ISSUE-64 | High | **CLOSED** | R24 (R31) |

**全部 8 项专利缺陷 + 1 项工程缺陷已关闭。**

---

## 5. 最终授权概率评估

| 场景 | 概率 | 备注 |
|------|------|------|
| 当前文本直接提交 | **40-50%** | 说明书 847 行、10 项引证、全覆盖 prior art 对照 |
| + 专业代理人润色 | **60-70%** | 代理人优化权利要求层次 + IPC 分类 + 摘要独立页 |
| 授权后抵御无效挑战 | **25-40%** | 取决于最终授权范围宽窄 |

---

## 6. 项目专利工作总结

从 R21 的 "NOT READY for filing" (15-25%) 到 R25 的 "filing-ready" (40-50%)，经历：
- R31: 4 Critical 修复（权利要求重构 + 说明书 7x 扩写 + 背景引证 + 变量名清理）
- R32: Prior art 全覆盖（英文文献 claim-level 对照 + CN-RS-06 修正 + 全球矩阵）

**建议下一步**：
1. 将 v3 文档打包交给专利代理人做最终润色
2. 代理人需关注：摘要独立页、IPC 分类（G06F 9/50）、权利要求措辞法律化
3. 可选：生成"元素级风险附录"供代理人参考

---

*Reviewed by Claude Opus 4.6 — 2026-02-13*
*本轮标志：R21 提出的全部 8 项专利缺陷已关闭*
