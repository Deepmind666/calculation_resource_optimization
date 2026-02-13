# 资源调度 Claim Chart（R14 修订）

- Timestamp: 2026-02-11 13:20:00 +08:00
- Owner: Codex (GPT-5)
- 目标: 以“3 个核心保护点”为中心，做可核验对照

## 1. 核心保护点定义

1. `CP-1`：per-GPU 亲和性准入投影  
   - 目标卡投影 + 同 tick 按卡累计 + unbound 保守分治
2. `CP-2`：瓶颈资源定向抢占  
   - 识别紧急维度（内存/GPU）+ 热点卡 + affinity 权重 + 双目标回收
3. `CP-3`：双视图模式判定与累计准入联合闭环  
   - raw 紧急判定 + EMA 稳态判定 + 迟滞冷却 + 同 tick 累计投影

## 2. 代码证据锚点

| 保护点 | 代码锚点 |
|---|---|
| CP-1 | `prototype/resource_scheduler.py:496`, `prototype/resource_scheduler.py:555`, `prototype/resource_scheduler.py:562`, `prototype/resource_scheduler.py:564` |
| CP-2 | `prototype/resource_scheduler.py:694`, `prototype/resource_scheduler.py:714`, `prototype/resource_scheduler.py:747`, `prototype/resource_scheduler.py:791` |
| CP-3 | `prototype/resource_scheduler.py:432`, `prototype/resource_scheduler.py:440`, `prototype/resource_scheduler.py:458`, `prototype/resource_scheduler.py:301`, `prototype/resource_scheduler.py:317` |

## 3. 回归与实验证据锚点

| 保护点 | 测试/实验证据 |
|---|---|
| CP-1 | `prototype/tests/test_resource_scheduler.py:516`, `prototype/tests/test_resource_scheduler.py:623`, `prototype/run_advanced_research.py` (P-04) |
| CP-2 | `prototype/tests/test_resource_scheduler.py:975`, `prototype/tests/test_resource_scheduler.py:1094`, `prototype/run_advanced_research.py` (P-05) |
| CP-3 | `prototype/tests/test_resource_scheduler.py:213`, `prototype/tests/test_resource_scheduler.py:460`, `prototype/run_patent_evidence.py:161`, `prototype/run_patent_evidence.py:230` |

## 4. 对照分析

| 保护点 | 最接近公开资料 | 已公开内容 | 本项目差异 | 新颖性风险 |
|---|---|---|---|---|
| CP-1 | K8s DRA + ResourceQuota + BinPacking | 有设备资源管理和总量控制 | 未见“目标卡 + unbound 保守分治 + 同 tick 按卡累计投影”闭环 | 中 |
| CP-2 | US20200167197A1 + K8s preemption + Slurm preemption | 有资源感知预抢占与优先级驱逐 | 本项目强调“归一化评分 + 热点卡亲和权重 + 双目标停止”组合 | 高 |
| CP-3 | EMA/阈值控制常规方案 + 资源配额 | 有平滑、阈值、配额思路 | 未见“raw 紧急旁路 + EMA 稳态 + 迟滞冷却 + 同 tick 累计投影”联合主张 | 中 |

## 5. 权利要求收敛建议

1. 独立权利要求绑定 CP-1 + CP-2 + CP-3，不拆单点。
2. 从属权利要求分别锁定：
   - CP-1 的 bound/unbound 分治与按卡累计规则；
   - CP-2 的 affinity 权重参数与双目标停止条件；
   - CP-3 的 raw 与 EMA 分工、迟滞与冷却关系。
3. 避免把“三级模式、EMA、迟滞、抢占”分别独立主张，显而易见风险高。

## 6. 当前判定

1. 工程可落地性：高（已有代码和测试覆盖）。
2. 发明专利可行性：中低（CP-2 受 RS-P01 高风险约束，需 claim-level 差异化）。
3. 建议路线：先完成专利全文检索，再决定发明直申或实用新型优先。
