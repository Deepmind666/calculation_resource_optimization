# 专利发表潜力自评（资源调度算法）

- 时间戳：2026-02-10 10:31:36 +08:00
- 执行人：Codex (GPT-5)
- 评估对象：`prototype/resource_scheduler.py` 及 `spec/` 主线文档
- 目的：给出当前可专利化潜力的工程侧自评，不替代正式法律意见。

## 1. 当前可主张的技术点

### P-01 多层防爆调度闭环
- 内容：`NORMAL/HIGH/EMERGENCY` 三态调度 + 准入控制 + 紧急抢占回收。
- 工程证据：`prototype/resource_scheduler.py:336`, `prototype/resource_scheduler.py:391`, `prototype/resource_scheduler.py:525`

### P-02 “原始峰值优先 + 平滑稳态”双视图判定
- 内容：紧急判定看 raw，稳态切换看 EMA + 滞回 + 冷却。
- 工程证据：`prototype/resource_scheduler.py:209`, `prototype/resource_scheduler.py:336`, `prototype/resource_scheduler.py:344`, `prototype/resource_scheduler.py:353`
- 价值：兼顾“防漏检”与“防抖动”，是较有表达力的差异化点。

### P-03 同一 tick 的累计准入预算
- 内容：每放行一个任务，立刻计入 planned load，再判断后续任务，防止同 tick 过量放行。
- 工程证据：`prototype/resource_scheduler.py:215`, `prototype/resource_scheduler.py:233`, `prototype/resource_scheduler.py:244`

### P-04 紧急回收的可解释策略
- 内容：按低优先级 + 高内存估算优先回收，并支持按目标回收量提前停止。
- 工程证据：`prototype/resource_scheduler.py:521`, `prototype/resource_scheduler.py:527`, `prototype/resource_scheduler.py:541`

## 2. 专利发表潜力评分（工程自评）
- 技术完整度：8/10（架构、代码、测试、实验脚本已具备）
- 新颖性潜力：6/10（各子技术常见，组合方式有一定可主张空间）
- 非显而易见性风险：中高（需证明“组合顺序/联动机制”带来可量化收益）
- 可实施性：8/10（可运行原型 + 自动校验 + 单测）
- 复现与审计性：7/10（日志与指标具备，仍需长期压测证据）

综合结论：当前处于“可申报准备期（非可直接提交期）”。

## 3. 主要短板与风险

### A-01 近似技术重叠风险
- 风险：资源调度、阈值保护、任务抢占本身属于成熟领域，单点创新难成立。
- 建议：把权利要求聚焦在“多机制联动顺序 + 约束关系 + 可测效果”。

### A-02 证据链不足
- 风险：目前实验以脚本化场景为主，真实负载与极端边界证据不足。
- 建议：补充真实进程池压力测试和失败注入实验，形成对照曲线。

### A-03 文档与专利文本映射尚未收敛
- 风险：需要把“代码机制 -> 权利要求术语 -> 说明书实施例”做一一映射。
- 建议：构建 claim-support matrix（按独立权利要求拆解证据段落）。

## 4. 建议的下一轮可执行计划（对齐 Claude 对比）
1. 固化 Claim 候选：围绕 `P-02 + P-03` 形成 1 条独立权利要求草案。
2. 做 3 组对照实验：
   - 基线 A：无 EMA/无冷却
   - 基线 B：无累计准入预算
   - 基线 C：无紧急抢占
3. 输出量化指标：OOM/崩溃事件、紧急持续时长、任务完成率、平均等待时长。
4. 形成“技术效果-证据表”：每条 claim 至少 2 组实验支持。

## 5. 下轮与 Claude 对比建议维度
- 是否认可 `F-01~F-04` 已闭环。
- 是否把 `R-01/R-02` 提升为必须修复项。
- 是否认可 `P-02/P-03` 作为主独立权利要求核心。
- 是否要求新增真实压力测试作为提交门槛。
