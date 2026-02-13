# Technique-Claim Mapping (Resource Scheduler v2)
- Timestamp: 2026-02-13 11:55:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: 将 v2 权利要求映射到当前代码、测试与真机证据，特别补充 R23 自适应重试。

## 1. 核心映射表

| 权利要求点 | 技术特征 | 代码证据 | 测试证据 | 实验证据 |
|---|---|---|---|---|
| CP-1 | 双视图模式判定（raw 紧急 + EMA 稳态） | `prototype/resource_scheduler.py:396`, `prototype/resource_scheduler.py:458`, `prototype/resource_scheduler.py:522` | `prototype/tests/test_resource_scheduler.py:214`, `prototype/tests/test_resource_scheduler.py:156`, `prototype/tests/test_resource_scheduler.py:171` | `figures/patent_evidence_metrics.json`（P-02） |
| CP-1A | 同 tick 累计准入投影（防超发） | `prototype/resource_scheduler.py:522` | `prototype/tests/test_resource_scheduler.py:461`, `prototype/tests/test_resource_scheduler.py:1496` | `figures/patent_evidence_metrics.json`（P-03） |
| CP-1B | per-GPU 亲和准入投影 | `prototype/resource_scheduler.py:444`, `prototype/resource_scheduler.py:522` | `prototype/tests/test_resource_scheduler.py:508`, `prototype/tests/test_resource_scheduler.py:737` | `figures/advanced_research_metrics_R24_completed_ge5_2026-02-13.json`（P-04） |
| CP-2 | 瓶颈资源定向抢占 + 归一化评分 + 双目标回收 | `prototype/resource_scheduler.py:734`, `prototype/resource_scheduler.py:674`, `prototype/resource_scheduler.py:715` | `prototype/tests/test_resource_scheduler.py:1156`, `prototype/tests/test_resource_scheduler.py:912`, `prototype/tests/test_resource_scheduler.py:772` | `figures/advanced_research_metrics_R24_completed_ge5_2026-02-13.json`（P-05） |
| CP-3 | 事件驱动双目标重试（安全+吞吐） | `prototype/run_advanced_research.py:1175`, `prototype/run_advanced_research.py:1217` | `prototype/tests/test_advanced_research.py:325` | `figures/real_baseline_eventful_R24_summary_2026-02-13.json` |
| CP-3A | 按失败原因分支的自适应重试（R23） | `prototype/run_advanced_research.py:903`, `prototype/run_advanced_research.py:915`, `prototype/run_advanced_research.py:1274`, `prototype/run_advanced_research.py:1313`, `prototype/run_advanced_research.py:1322` | `prototype/tests/test_advanced_research.py:250`, `prototype/tests/test_advanced_research.py:263`, `prototype/tests/test_advanced_research.py:325` | `figures/real_baseline_eventful_R24_summary_2026-02-13.csv` |
| CP-4 | 审计可追溯字段（threshold_bias / adaptation_action / retry_reason） | `prototype/run_advanced_research.py:1281`, `prototype/run_advanced_research.py:1282`, `prototype/run_advanced_research.py:1304`, `prototype/run_advanced_research.py:1527`, `prototype/run_advanced_research.py:1528` | `prototype/tests/test_advanced_research.py:325` | `figures/advanced_research_metrics_R24_completed_ge5_2026-02-13.csv` |

## 2. R23 关键证据摘要（R24 真机）

数据来源：
1. `figures/real_baseline_eventful_R24_summary_2026-02-13.json`
2. `figures/real_baseline_eventful_R24_summary_2026-02-13.csv`

结论：
1. `eventful_achieved=1`，`attempts_executed=5`，`min_completed=5`，`final_completed=7`。
2. 轨迹中同时出现三类失败原因并触发对应分支动作：  
 - `low_signal_dynamic` -> `tighten_and_escalate`  
 - `missing_emergency_signal` -> `tighten_and_escalate`  
 - `insufficient_completion` -> `relax_and_hold`
3. 最终满足双目标停止条件：安全信号存在（`emergency_ticks=3` 或 `preempted_total=1`）且吞吐达标（`completed=7`）。

## 3. 与 v2 权利要求对应关系
1. `patent/权利要求书_资源调度_v2.md` Claim 1 对应 CP-1 + CP-2 + CP-3 组合。
2. Claim 9~12 对应 CP-3A 与 CP-4（R23 分支规则与审计轨迹）。
3. Claim 15~16 对应系统模块化实现中的自适应重试控制与审计输出。

## 4. 复核清单
- [x] 代码行号已按当前工作树重新对齐
- [x] R23 新增字段有代码证据 + 测试证据 + 真机证据
- [x] 权利要求术语与实现术语一致（threshold bias / adaptation action / retry reason）
