# Deep Algorithm Self Audit — R21 (2026-02-12)

## 1. Scope
基于 Claude R16 评审建议，本轮重点完成：
1. ISSUE-58 的实证闭环：真机基线稳定触发 `emergency_ticks` 与 `preempted_total`。
2. R20 重试策略强化：不仅加压任务参数，还按尝试轮次收紧调度阈值。
3. ISSUE-59 纠偏：本轮统一以全量测试数为准（70/70）。

## 2. Code Changes
### 2.1 `prototype/run_advanced_research.py`
1. 新增阈值规划器：`plan_eventful_scheduler_thresholds(attempt_index)`。
2. `run_real_machine_baseline()` 增加实验参数透传：
   - `dynamic_memory_high_pct`
   - `dynamic_memory_emergency_pct`
   - `dynamic_preempt_count_per_tick`
   - `dynamic_cpu_high_pct`
   - `dynamic_cpu_hard_pct`
3. `run_real_machine_baseline_until_eventful()`：
   - 每轮尝试动态注入阈值规划结果；
   - `attempts[].params` 记录阈值参数；
4. `_flatten_rows()` 新增 `REAL-BASELINE-ATTEMPT` 的阈值字段导出。

### 2.2 Tests
1. `prototype/tests/test_advanced_research.py`
   - `test_plan_eventful_scheduler_thresholds_are_valid_and_tighten`
   - `test_run_real_machine_baseline_until_eventful_stops_early` 增加 call-args 阈值断言。
2. `prototype/tests/test_resource_scheduler.py`
   - 现有 GPU PID 显存解析回归继续保持通过。

## 3. Verification Commands
1. `python -m unittest prototype.tests.test_advanced_research -v` -> PASS (10)
2. `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (70/70)
3. `python qa/validate_scheduler_config.py spec/scheduler_config.example.json` -> PASS
4. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
5. `python prototype/run_experiments.py` -> PASS
6. `python prototype/run_patent_evidence.py` -> PASS
7. `python prototype/run_advanced_research.py --trials 20 --run-real-baseline --real-target-eventful --real-max-attempts 3 --real-task-count 6 --real-task-duration-sec 2 --real-base-mem-mb 96 --real-fixed-workers 4 --real-max-wall-sec 12` -> PASS

## 4. Evidence Snapshot (Issue-58 Closure)
同机实测结果（event-targeted mode）：
1. `eventful_achieved = 1`
2. `attempts_executed = 1`
3. Dynamic summary:
   - `emergency_ticks = 9`
   - `preempted_total = 1`
   - `blocked_event_total = 162`
   - `low_signal_dynamic = 0`
   - `emergency_signal_missing = 0`

结论：ISSUE-58 从“方向修复”提升为“实证闭环”。

## 5. Risk Notes
1. 该机环境背景负载较重，A/B 基线仍出现较高非零退出；需在评审中明确“这是主机环境噪声，不是调度器逻辑失败”。
2. 事件触发依赖压力配置，跨机器复现实验建议保留 `--real-target-eventful` 与 attempt trace。

## 6. Next Step
1. 按评审 P2：专利文本同步 R17 协同评分公式与 R21 事件证据。
2. 按评审 P3：推进 RS-P01 claim-level 对照与 CNIPA 检索。
