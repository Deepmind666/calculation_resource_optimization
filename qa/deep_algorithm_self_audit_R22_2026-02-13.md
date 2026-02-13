# Deep Algorithm Self Audit — R22 (2026-02-13)

## 1. Scope
根据 R18 评审后的下一步要求，补充“安全 + 吞吐”双目标证据能力，并修复真机实验中的 GPU 峰值异常值污染问题。

## 2. Spec-first Updates
1. `spec/architecture.md`
   - 增加 R22 双目标证据模式（安全目标 + 吞吐目标 + 重试原因）。
   - 增加 GPU 峰值数据质量门槛。
2. `spec/algorithm_pseudocode.md`
   - `need_eventful_retry` 升级为返回 `(retry, reason)` 并支持 `require_completion/min_completed`。
   - `run_real_baseline_until_eventful` 增加 completion 约束与 wall 时间自适应。
3. `spec/data_model.md`
   - 补充 `retry_reason` 与双目标模式字段语义。

## 3. Test-first Additions
1. `prototype/tests/test_advanced_research.py`
   - `test_need_eventful_retry_can_require_completion`
   - `test_run_real_machine_baseline_until_eventful_with_completion_requirement`
   - `test_sample_gpu_peak_percent_skips_absurd_rows`
   - existing tests updated for tuple return `(retry, reason)`.

## 4. Implementation Changes
1. `prototype/run_advanced_research.py`
   - `need_eventful_retry(...) -> Tuple[bool, str]`
   - `run_real_machine_baseline_until_eventful(...)` 支持：
     - `require_completion`
     - `min_completed`
     - `retry_reason` 记录
     - completion 不足时自动增加 `max_scheduler_wall_sec`
   - CLI 新增：
     - `--real-require-completion`
     - `--real-min-completed`
   - `REAL-BASELINE-ATTEMPT` 输出新增：
     - `completed`
     - `retry_reason`
     - `max_scheduler_wall_sec`
2. GPU 峰值采样健壮性修复：
   - `_sample_gpu_peak_percent` 过滤 `total < 1` 与离谱比例（`pct > 1000`），并约束结果到 `[0, 100]`。

## 5. Verification
1. `python -m unittest prototype.tests.test_advanced_research -v` -> PASS (13)
2. `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (73/73)
3. `python qa/validate_scheduler_config.py spec/scheduler_config.example.json` -> PASS
4. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
5. `python prototype/run_experiments.py` -> PASS
6. `python prototype/run_patent_evidence.py` -> PASS
7. `python -m py_compile prototype/run_advanced_research.py prototype/tests/test_advanced_research.py prototype/tests/test_resource_scheduler.py` -> PASS

## 6. Real-run Evidence
Command:
`python prototype/run_advanced_research.py --trials 20 --run-real-baseline --real-target-eventful --real-require-completion --real-min-completed 1 --real-max-attempts 3 --real-task-count 6 --real-task-duration-sec 2 --real-base-mem-mb 96 --real-fixed-workers 4 --real-max-wall-sec 12`

Observed:
1. Dual-target mode executed correctly with 3 attempts and traceable reasons:
   - `missing_emergency_signal`
   - `insufficient_completion`
   - `low_signal_dynamic`
2. This host still did not achieve dual-target in 3 attempts (`eventful_achieved=0`), but retry logic, reason reporting, and wall-time adaptation all worked as designed.

## 7. Risks
1. 主机背景负载较高时，双目标达成依然可能失败，需要更多 attempt 或更轻环境复核。
2. 真机证据应附带 attempt trace，避免单次结论误导。

## 8. Next Step
1. 增加“环境预检”并在高背景负载下自动建议切换到低负载窗口（或降并发任务集）。
2. 推进评审建议的 P2/P3：专利文本同步 + CNIPA/RS-P01 claim-level 工作。
