# Deep Algorithm / Patent Self Audit - R24 (2026-02-13)

## 1. Scope
基于 R19 评审结论，执行两项优先任务：
1. P1：补齐专利文本（R23 自适应重试机制 + 从属权利要求 + 附图说明）。
2. P3：用更强真机参数获得 `completed >= 5` 的双目标实证，并固化快照。

## 2. Deliverables
1. `patent/权利要求书_资源调度_v2.md`
2. `patent/说明书_资源调度_v2.md`
3. `patent/附图说明_资源调度_v2.md`
4. `patent/附图_资源调度_图3_真机三模式对比.svg`
5. `patent/附图_资源调度_图4_自适应重试轨迹.svg`
6. `qa/technique_claim_mapping_resource_scheduler_v2_2026-02-13.md`
7. `figures/advanced_research_metrics_R24_completed_ge5_2026-02-13.json`
8. `figures/advanced_research_metrics_R24_completed_ge5_2026-02-13.csv`
9. `figures/real_baseline_eventful_R24_summary_2026-02-13.json`
10. `figures/real_baseline_eventful_R24_summary_2026-02-13.csv`

## 3. Real-Machine Command and Result
Command:
`python prototype/run_advanced_research.py --trials 50 --run-real-baseline --real-target-eventful --real-require-completion --real-min-completed 5 --real-max-attempts 6 --real-task-count 8 --real-task-duration-sec 6 --real-base-mem-mb 2048 --real-fixed-workers 4 --real-max-wall-sec 24`

Observed:
1. `eventful_achieved=1`
2. `attempts_executed=5`
3. `final_completed=7` (>=5 target satisfied)
4. `final_emergency_ticks=3`
5. `final_preempted_total=1`

R23 branch trace evidence:
1. `low_signal_dynamic` -> `tighten_and_escalate`
2. `missing_emergency_signal` -> `tighten_and_escalate`
3. `insufficient_completion` -> `relax_and_hold`
4. `satisfied` -> stop

## 4. Claim-Level Mapping Update
`qa/technique_claim_mapping_resource_scheduler_v2_2026-02-13.md` 新增对 CP-3/CP-3A/CP-4 的映射：
1. CP-3：双目标事件驱动重试。
2. CP-3A：按失败原因分支自适应阈值。
3. CP-4：`threshold_bias/adaptation_action/retry_reason` 审计字段导出。

## 5. Validation
1. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
2. `python qa/validate_scheduler_config.py` -> PASS
3. `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (75/75)
4. SVG parse check (PowerShell XML) for Figure 3/4 -> PASS

## 6. Risks
1. 真机数据受宿主机背景任务影响，建议后续增加 repeated-runs CI 汇总置信区间。
2. RS-P01 与 CNIPA 的全文权利要求级对比仍未闭环（ISSUE-55 / ISSUE-51）。

## 7. Next Step
1. P2：执行 CNIPA 检索与 RS-P01 逐条权利要求对照，补全文献风险矩阵。
2. 做 `real-target-eventful` repeated runs 的统计摘要（达成率、完成数分布、CI）。
