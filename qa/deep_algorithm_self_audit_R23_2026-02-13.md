# Deep Algorithm Self Audit - R23 (2026-02-13)

## 1. Scope
本轮目标是修复 R18 后续遗留的“真机双目标收敛粗糙”问题：  
在 `real-target-eventful + require_completion` 场景下，引入按重试原因分支的自适应阈值策略，提升“安全证据 + 吞吐证据”同时达成的概率，并保持全链路可审计。

## 2. Spec-First Changes
先更新 `spec/`，后改 `prototype/`：
1. `spec/algorithm_pseudocode.md`
   - 新增 `apply_eventful_threshold_bias` 与 `update_eventful_threshold_bias` 伪代码。
   - 明确重试分支：
     - `insufficient_completion` -> 放宽阈值并延长 wall budget；
     - `low_signal_dynamic` / `missing_emergency_signal` -> 收紧阈值并升压。
2. `spec/architecture.md`
   - 新增 R23 段落，定义双目标自适应收敛机制及审计要求。
3. `spec/data_model.md`
   - 新增 attempt trace 字段语义：`threshold_bias`、`adaptation_action`。

## 3. Test-First Changes
`prototype/tests/test_advanced_research.py` 新增/强化：
1. `test_apply_eventful_threshold_bias_is_reasonable`
2. `test_update_eventful_threshold_bias_rules`
3. `test_run_real_machine_baseline_until_eventful_with_completion_requirement`
   - 验证 `insufficient_completion` 分支会放宽阈值；
   - 验证该分支不再盲目升压 workload 参数；
   - 验证 wall budget 增长逻辑保留。

## 4. Implementation Changes
`prototype/run_advanced_research.py`：
1. 新增函数：
   - `apply_eventful_threshold_bias(base_cfg, threshold_bias)`
   - `update_eventful_threshold_bias(current_bias, retry_reason)`
2. `run_real_machine_baseline_until_eventful(...)` 改为原因分支驱动：
   - `insufficient_completion`: `adaptation_action=relax_and_hold`，延长 wall budget，保持 workload 参数；
   - 其他重试原因：`adaptation_action=tighten_and_escalate`，执行 workload 升压；
   - 每轮记录 `threshold_bias`、`adaptation_action`。
3. CSV flatten 输出新增：
   - `threshold_bias`
   - `adaptation_action`

## 5. Validation Commands
1. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
2. `python qa/validate_scheduler_config.py` -> PASS
3. `python -m unittest prototype.tests.test_advanced_research -v` -> PASS (15 tests)
4. `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (75/75)
5. `python prototype/run_experiments.py` -> PASS
6. `python prototype/run_patent_evidence.py` -> PASS
7. `python -m py_compile prototype/run_advanced_research.py prototype/tests/test_advanced_research.py` -> PASS

## 6. Real-Machine Evidence (This Round)
Command:
`python prototype/run_advanced_research.py --trials 20 --run-real-baseline --real-target-eventful --real-require-completion --real-min-completed 1 --real-max-attempts 4 --real-task-count 6 --real-task-duration-sec 2 --real-base-mem-mb 96 --real-fixed-workers 4 --real-max-wall-sec 12`

Observed key output:
1. `eventful_achieved=1`, `attempts_executed=2`
2. 第 2 轮达成：`completed=3`, `emergency_ticks=13`, `preempted_total=2`
3. attempt trace 含：
   - `threshold_bias`
   - `adaptation_action`
   - `retry_reason`
   - 动态阈值与 wall budget

结论：本轮在真机上拿到了“安全 + 吞吐”同轮证据，不是仅安全零吞吐。

## 7. Risks
1. 真实主机背景负载波动仍会影响 attempt 收敛速度；
2. `max_scheduler_wall_sec` 较小时，可能出现 `scheduler_timeout_hit=1` 且存在 unfinished tasks；
3. 结果复现实验应固定 seed 与参数，并保留完整 attempt trace。

## 8. Next Step
1. 在 R23 基础上做多轮 CI（真实基线 repeated runs）并输出双目标达成率区间；
2. 将 R23 字段映射补入专利 claim mapping（技术点 -> 代码行 -> 实验字段）。
