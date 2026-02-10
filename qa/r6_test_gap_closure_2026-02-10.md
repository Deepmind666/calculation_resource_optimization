# R6 缺口测试补齐报告

- 时间戳：2026-02-10 13:32:05 +08:00
- 执行人：Codex (GPT-5)
- 目标：补齐 R5 指出的 4 类测试缺口（迟滞、GPU联动、回收目标、real-run 投影）。

## 1. 补齐结果总览

| 类别 | 状态 | 测试用例 | 证据 |
|---|---|---|---|
| 迟滞退出（hysteresis） | 已补齐 | `test_hysteresis_memory_exit_stays_high` | `prototype/tests/test_resource_scheduler.py:152` |
| 迟滞退出（GPU） | 已补齐 | `test_hysteresis_gpu_exit_stays_high` | `prototype/tests/test_resource_scheduler.py:167` |
| GPU 准入与紧急联动 | 已补齐 | `test_gpu_admission_blocks_projected_emergency`, `test_gpu_admission_and_emergency_linkage` | `prototype/tests/test_resource_scheduler.py:338`, `prototype/tests/test_resource_scheduler.py:347` |
| 智能回收目标验证 | 已补齐 | `test_reclaim_target_stops_after_enough_reclaimed` | `prototype/tests/test_resource_scheduler.py:406` |
| real-run 同 tick 投影 | 已补齐 | `test_real_run_projection_blocks_second_start_same_tick` | `prototype/tests/test_resource_scheduler.py:541` |

## 2. 关键断言摘要

1. 迟滞：在阈值回落但未跌破退出阈值时，模式保持 `HIGH`。
2. GPU准入：当 projected GPU 显存达到紧急阈值时准入被阻断。
3. GPU联动：GPU 紧急峰值可触发 `EMERGENCY` 并联动抢占。
4. 回收目标：达到 `reclaim_needed_mb` 后抢占提前停止，避免过度回收。
5. real-run 投影：同一 tick 启动第 1 个真实任务后，第 2 个可被投影阻断，防止快照延迟带来的超发。

## 3. 全量复验

```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```

结果：
1. `25/25` 测试通过。
2. 配置校验 PASS。
3. 结构检查 PASS。

## 4. 结论

R6 第 2 步（测试缺口补齐）已完成，当前进入“稳定可评审”状态，可继续推进第 3 步（可专利证据包），前提是你确认继续资源调度方向。
