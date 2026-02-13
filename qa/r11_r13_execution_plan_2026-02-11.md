# R11-R13 执行计划（深度解析后）

- Timestamp: 2026-02-11 12:31:00 +08:00
- Owner: Codex (GPT-5)
- Input basis:
  - `qa/claude_review_R10_2026-02-11.md`（ISSUE-36/37）
  - `qa/claude_review_R9_2026-02-11.md`
  - 用户提供的“专利推进/测试盲区/实验不足”评审意见

## 1) 深度解析结论

### 1.1 代码与算法状态（当前）
1. 调度器主干已到生产可用级：F-01~F-24 全部闭环，`44/44` 测试通过。
2. 当前剩余算法问题主要是两个 Low 级：
   - ISSUE-36：`_preempt_low_priority` 维度判断使用 smoothed 视图，和 `_evaluate_mode` 的 raw 紧急判定策略不一致。
   - ISSUE-37：混合紧急场景评分仍存在 mem/gpu 单位混合，影响“效率最优”，不影响“安全正确”。
3. 结论：下一轮应先做一致性与评分归一化，继续提升“可解释性 + 抢占效率”。

### 1.2 专利状态（当前）
1. `patent/` 与 `prior_art/` 仍是旧方向遗留，和当前资源调度实现不对齐。
2. 当前 P-02/P-03 证据可用于“技术说明”，但不足以支撑强新颖性主张。
3. 结论：专利推进的前置条件是“资源调度领域正式检索 + 文档重写”，否则继续写权利要求意义有限。

### 1.3 测试与实验状态（当前）
1. 单测覆盖面已广，但存在系统性盲区：
   - 真实进程生命周期覆盖不足
   - 长序列鲁棒性不足
   - 估算误差容错能力未量化
2. 实验脚本以消融和合成序列为主，尚未形成“真实工作负载证据”。
3. 结论：需要补一轮“真实负载 + 基线对比 + 参数敏感性”的最小可行实验集。

## 2) 下一步总体策略

1. 先完成算法一致性闭环（R11），把 ISSUE-36/37 清零。
2. 再补测试盲区（R12），确保评审从“逻辑正确”提升到“运行可靠”。
3. 并行启动专利前置工程（R13），先检索、后写作、再做路线决策（发明/实用新型）。

## 3) R11 计划（算法一致性与效率）

### 3.1 目标
1. 修复 ISSUE-36：紧急维度判定统一使用 raw emergency view。
2. 优化 ISSUE-37：混合紧急评分改为归一化双维评分，避免单位混合。

### 3.2 拟实施改动
1. `prototype/resource_scheduler.py`
   - 将 `raw_snapshot` 传入 `_preempt_low_priority(...)`。
   - 增加 `emergency_view = raw_snapshot or snapshot` 并仅用其判断 `memory_emergency/gpu_emergency`。
   - 将抢占评分调整为归一化形式，例如：
     - `mem_score = estimated_mem_mb / max(1.0, reclaim_needed_mem_mb)`
     - `gpu_score = effective_gpu_reclaim / max(1.0, reclaim_needed_gpu_mb)`
     - `combined = w_mem * mem_score + w_gpu * gpu_score`
   - 默认 `w_mem=1.0`, `w_gpu=1.0`，保持行为可解释。
2. `prototype/tests/test_resource_scheduler.py`
   - 新增 raw/smoothed 分歧回归测试（验证 ISSUE-36）。
   - 新增混合紧急归一化排序测试（验证 ISSUE-37）。
3. 文档同步：
   - `spec/algorithm_pseudocode.md`
   - `spec/data_model.md`
   - `qa/deep_algorithm_self_audit_R11_*.md`

### 3.3 验收标准
1. 全量测试通过且新增测试覆盖 ISSUE-36/37。
2. 不引入 F-21/F-22/F-23/F-24 回归。
3. 行号映射与审计文档同步更新。

## 4) R12 计划（测试盲区补齐）

### 4.1 目标
1. 补真实进程生命周期验证。
2. 补长序列随机扰动鲁棒性。
3. 补估算误差容错测试。

### 4.2 最小可行测试集
1. Real-process integration（dry_run=False）：
   - 启动短时真实子进程，验证完成路径。
   - 启动超时子进程，验证 timeout/stop/stuck 指标链路。
2. Long-run robustness：
   - 100~500 ticks 随机噪声 snapshot（固定 seed）；
   - 断言无状态退化（队列/指标/事件上限）。
3. Estimation error：
   - 任务估算与“真实执行足迹”偏差 0.5x~3x；
   - 验证阻断率/预抢占行为在可接受范围内。

### 4.3 验收标准
1. 新增测试稳定通过（无 sleep 依赖脆弱断言）。
2. 回归总数增长且覆盖新增风险维度。
3. 测试运行时间控制在可接受范围。

## 5) R13 计划（专利前置与证据升级）

### 5.1 目标
1. 重建资源调度方向 prior art。
2. 重写 `patent/` 全套文档为当前实现方向。
3. 输出“发明 vs 实用新型”路线建议书。

### 5.2 产出文件（计划）
1. `prior_art/resource_scheduler_search_plan.md`
2. `prior_art/resource_scheduler_prior_art_index.md`
3. `prior_art/resource_scheduler_claim_chart.md`
4. `patent/权利要求书_资源调度_v1.md`
5. `patent/说明书_资源调度_v1.md`
6. `qa/patent_route_decision_report_2026-02-11.md`

### 5.3 核心保护点（建议保持 3 条）
1. per-GPU 亲和性准入投影（bound/unbound 分治 + 同 tick 分桶累计）。
2. 瓶颈资源定向抢占（热点卡 + affinity 权重 + 双目标回收）。
3. 双视图判定与同 tick 累计投影的联合闭环（raw 紧急 + EMA 稳态 + 迟滞冷却 + 累计预算）。

### 5.4 验收标准
1. prior art 至少形成资源调度领域可追溯证据链。
2. 新权利要求文本与代码特征逐项映射。
3. 给出明确路线建议（发明继续/转实用新型）。

## 6) 执行节奏建议

1. D1-D2：R11（ISSUE-36/37 + 新测试 + 文档同步）。
2. D2-D4：R12（真实进程 + 长序列 + 误差容错测试）。
3. D3-D6：R13（prior art 重建 + patent 重写 + 决策报告）。

## 7) 风险与控制

1. 风险：真实负载实验依赖本机环境差异。
   - 控制：固定 seed、固定脚本参数、记录硬件与配置快照。
2. 风险：prior art 检索深度不足导致路线误判。
   - 控制：按 CPC + 多库检索并建立检索日志。
3. 风险：权利要求过宽导致显而易见驳回。
   - 控制：坚持“3 个不可分拆组合点”并由代理人二次收敛。

## 8) 立即执行项（无需等待决策）

1. 立刻启动 R11：修 ISSUE-36/37。
2. 同步新增 R11 审计文档与日志条目。
3. R11 完成后再进入 R12 的真实进程测试增强。
