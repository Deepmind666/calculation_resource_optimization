# RS-P01 Claim-Level 对照（US20200167197A1 / US11656911B2）

- Timestamp: 2026-02-11 13:20:00 +08:00
- Owner: Codex (GPT-5)
- 文献：
  - https://patents.google.com/patent/US20200167197A1/en
  - https://patents.google.com/patent/US11656911B2/en
- 目的：响应 ISSUE-45，对高风险近似技术做逐条差异化

## 1. RS-P01 关键权利要素（摘要级 + claim 级）

基于公开 claim 文本可提炼的核心要素：
1. 资源发现引擎（compute resource discovery engine）
2. 待调度作业发现（pending workload detection）
3. 预抢占策略引擎（proactive preemption strategy）
4. 终止已有作业以释放资源（preemptive termination）
5. 释放后重调度高优先级作业（reschedule high-priority item）

## 2. 与本项目的逐条对照

| RS-P01 要素 | 本项目对应能力 | 重叠结论 | 差异化点（可用于抗驳回） |
|---|---|---|---|
| 资源发现引擎 | `ResourceMonitor` 周期采样 | 重叠 | 本项目进一步区分 raw/EMA 双视图用于不同决策层 |
| pending 发现 | `pending` 队列 + `submit_task` | 重叠 | 本项目含同 tick 累计投影预算，不是静态 pending 判定 |
| 预抢占策略 | `_preempt_low_priority` | 重叠 | 本项目为瓶颈维度定向 + 归一化评分 + GPU 热点识别 |
| 终止低优释放资源 | `_stop_task(reason=PREEMPTED)` | 重叠 | 本项目有 stuck 逃逸和双目标回收停止（内存+GPU） |
| 重调度高优任务 | tick 内重新 admission | 重叠 | 本项目含 per-GPU 目标卡投影与 unbound 保守分治 |

## 3. 高风险结论

1. RS-P01 与本项目在“资源感知 + 低优先级预抢占 + 高优先级保障”框架上高度重叠。
2. 因此其风险级别必须标为 `高`，不能标 `中`。
3. 本项目必须把差异化焦点收敛为组合特征，而非单点特征：
   - `raw 紧急 + EMA 稳态 + 迟滞冷却`
   - `同 tick 累计预算`
   - `per-GPU 亲和投影（bound/unbound 分治）`
   - `归一化多资源抢占评分 + 双目标回收`

## 4. 下一步（必须执行）

1. 将 RS-P01 family 的授权文本与从属权利要求做细粒度比对。
2. 输出“不可被 RS-P01 覆盖”的最小特征组合。
3. 与代理人协同重写独立权利要求，避免落入“显而易见组合”。
