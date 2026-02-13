# Deep Algorithm Self Audit — R19 (2026-02-12)

## 1. Scope
本轮聚焦两条主线：
1. 针对 R15/R18 链路补齐 GPU 画像自校准闭环（调度核心）。
2. 针对 ISSUE-58 强化真机基线实验有效性（参数规划 + 低信号标记）。

## 2. Implemented Changes
### 2.1 Scheduler core (`prototype/resource_scheduler.py`)
1. `TaskRuntime` 新增 `observed_peak_gpu_mem_mb`。
2. `ResourceProfile` 新增 `ema_peak_gpu_mem_mb`。
3. 新增 GPU 进程显存采样：
`_read_gpu_pid_memory_mb()` + `_gpu_usage_mb_for_pid()`（带采样间隔缓存）。
4. `_sample_runtime_usage()` 增加进程级 GPU 峰值观测。
5. `_update_resource_profile()` 增加 GPU EMA 更新与事件字段。
6. `_apply_estimation_profile()` 增加 GPU 估算自校准与事件字段。

### 2.2 Advanced research (`prototype/run_advanced_research.py`)
1. 新增 `plan_real_baseline_params()`：自动提升过弱参数并限制过载风险。
2. `run_real_machine_baseline()` 接入参数规划，输出 planning metadata。
3. 新增实验质量字段：
`started_total`, `low_signal_dynamic`, `emergency_signal_missing`, `cpu_clip_events`。
4. 新增 `CpuCappedMonitor`（实验专用）：缓解宿主机 CPU 100% 噪声导致的全阻断。
5. 调整真机负载任务 CPU 估算（memory-focused baseline）。
6. `summarize_real_baseline_runs()` 指标集合同步扩展。

### 2.3 Spec/docs synchronization
1. `spec/architecture.md`：补 R19 真机基线有效性约束。
2. `spec/algorithm_pseudocode.md`：补 GPU 自校准伪代码 + R19 参数规划/质量标记伪代码。
3. `spec/data_model.md`：补 `observed_peak_gpu_mem_mb` 与 `ResourceProfile.ema_peak_gpu_mem_mb`。
4. `prototype/README.md`、`figures/README.md`：补 R19 输出字段与使用说明。

## 3. Added/Updated Tests
### 3.1 `prototype/tests/test_resource_scheduler.py`
1. `test_task_profile_updates_with_gpu_ema`
2. `test_autocalibration_adjusts_gpu_estimate_on_submit`

### 3.2 `prototype/tests/test_advanced_research.py`
1. `test_plan_real_baseline_params_strengthens_weak_inputs`
2. `test_plan_real_baseline_params_reduces_oversized_task_count`

## 4. Verification Checklist
1. `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS (`65/65`)
2. `python qa/validate_scheduler_config.py spec/scheduler_config.example.json` -> PASS
3. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
4. `python prototype/run_experiments.py` -> PASS
5. `python prototype/run_patent_evidence.py` -> PASS
6. `python prototype/run_advanced_research.py --trials 20 --run-real-baseline --real-task-count 6 --real-task-duration-sec 2 --real-base-mem-mb 96 --real-fixed-workers 4 --real-max-wall-sec 20` -> PASS

## 5. Key Observations
1. 参数规划生效：`duration_sec` 从 `2` 提升到 `6`，`base_mem_mb` 从 `96` 提升到 `2048`。
2. 真机动态阶段不再“零启动伪通过”：
`started_total=3`，`completion_rate=0.5`。
3. 环境仍未触发 emergency/preempt 分支，已显式标记：
`emergency_signal_missing=1`，避免误判为“已覆盖紧急路径”。
4. 宿主机 CPU 高负载确实存在，`cpu_clip_events` 可追溯。

## 6. Residual Risks
1. 当前机器持续高负载，真机动态实验仍容易受外部任务干扰。
2. 仍缺“必触发 EMERGENCY + PREEMPT 的真机基线参数搜索器”（仅做了有效性标记，未自动二次升压重跑）。
3. GPU 进程采样依赖 `nvidia-smi --query-compute-apps`；不同驱动/权限下可能返回空结果。

## 7. Next Action (R20 candidate)
1. 增加“目标事件驱动”真机参数搜索（先小样本探针，再自动收敛到可触发 emergency 的区间）。
2. 在 real-baseline multi-run 中增加无效轮次剔除统计（按 `low_signal_dynamic` / `emergency_signal_missing`）。
3. 增加 1 条集成测试：mock `nvidia-smi --query-compute-apps` 验证 GPU PID 聚合解析。
