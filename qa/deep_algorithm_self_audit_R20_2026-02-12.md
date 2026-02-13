# Deep Algorithm Self Audit — R20 (2026-02-12)

## 1. Scope
本轮目标是把 R19 的“真机基线有效性标记”推进到“可自动收敛尝试”的 R20：
1. 目标事件驱动重试（event-targeted retry）。
2. 尝试轨迹可追溯输出（JSON/CSV）。
3. 增补 GPU 进程显存解析回归测试。

## 2. Main Changes
### 2.1 Spec first
1. `spec/architecture.md`：新增 R20 章节（目标事件驱动真机基线）。
2. `spec/algorithm_pseudocode.md`：新增 `need_eventful_retry` / `escalate_real_baseline_params` / `run_real_baseline_until_eventful` 伪代码。
3. `spec/data_model.md`：补充 R20 尝试轨迹数据字段说明。

### 2.2 Tests first
1. `prototype/tests/test_advanced_research.py`
   - `test_need_eventful_retry_flags`
   - `test_escalate_real_baseline_params_increases_pressure`
   - `test_run_real_machine_baseline_until_eventful_stops_early`
2. `prototype/tests/test_resource_scheduler.py`
   - `test_gpu_pid_memory_parser_aggregates_and_skips_invalid_rows`

### 2.3 Implementation
1. `prototype/run_advanced_research.py`
   - 新增 `_find_dynamic_row`
   - 新增 `need_eventful_retry`
   - 新增 `escalate_real_baseline_params`
   - 新增 `run_real_machine_baseline_until_eventful`
   - CLI 新增：
     - `--real-target-eventful`
     - `--real-max-attempts`
     - `--real-attempt-seed-step`
   - `_flatten_rows` 新增 `REAL-BASELINE-ATTEMPT` 导出。
2. 文档同步
   - `prototype/README.md`
   - `figures/README.md`

## 3. Verification Evidence
1. `python -m unittest prototype.tests.test_advanced_research -v` -> PASS（9 tests）
2. `python -m unittest prototype.tests.test_resource_scheduler.ResourceSchedulerTests.test_gpu_pid_memory_parser_aggregates_and_skips_invalid_rows -v` -> PASS
3. `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS（69/69）
4. `python qa/validate_scheduler_config.py spec/scheduler_config.example.json` -> PASS
5. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
6. `python prototype/run_experiments.py` -> PASS
7. `python prototype/run_patent_evidence.py` -> PASS
8. `python prototype/run_advanced_research.py --trials 10 --run-real-baseline --real-target-eventful --real-max-attempts 2 --real-task-count 6 --real-task-duration-sec 2 --real-base-mem-mb 96 --real-fixed-workers 4 --real-max-wall-sec 8` -> PASS

## 4. Key Observations
1. R20 能输出完整尝试轨迹：每轮参数 + 动态摘要 + 是否继续重试。
2. 本机高负载环境下，2 次尝试仍未触发 emergency/preempt（`eventful_achieved=0`），但已被系统明确标注，不会误判为“证据充分”。
3. 新增 GPU PID 显存解析测试验证了：
   - 同 PID 多行聚合；
   - 异常行跳过；
   - 单位噪声容忍（如 `MiB` 后缀）。

## 5. Residual Risks
1. 即使自动加压，受宿主机外部负载影响，仍可能达不到 emergency/preempt 目标事件。
2. 当前重试策略是启发式加压，尚未做“目标导向参数搜索”。

## 6. Next Step Proposal (R21)
1. 增加基于目标事件的自适应搜索器（优先调 `task_count/base_mem/duration/max_wall`）。
2. 给 `real_baseline_multirun` 增加“有效轮次占比”统计（过滤 `low_signal_dynamic=1`）。
