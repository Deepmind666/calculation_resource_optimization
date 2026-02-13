# prototype

本目录是“资源调度防爆”原型实现。

新增能力（R15）：任务资源估算自校准（基于真实运行观测更新画像并自动提高后续估算）。

核心文件：
1. `resource_scheduler.py`：资源监控、模式判定、接纳控制、紧急回收。
2. `main.py`：演示入口（默认 dry-run，安全）。
3. `run_experiments.py`：多场景实验并输出 CSV/JSON。
4. `run_patent_evidence.py`：P-02/P-03 消融证据输出。
5. `run_advanced_research.py`：P-04/P-05 大规模消融 + 可选真机基线实验。
6. `tests/test_resource_scheduler.py`：调度器主测试。
7. `tests/test_advanced_research.py`：高级实验脚本测试。

## 快速运行
```powershell
cd prototype
python main.py --ticks 12
python run_experiments.py
python run_patent_evidence.py
python run_advanced_research.py --trials 4000
python -m unittest discover -s tests -p "test_*.py"
cd ..
```

## 安全说明
1. `main.py` 默认 `dry-run`，不启动真实子进程。
2. 需要真实执行时再加 `--real-run`，且建议先小规模验证。
3. `run_advanced_research.py --run-real-baseline` 会真实启动负载进程，建议先用小参数试跑。

## Advanced Research Update (R16)
1. P-04 now uses mixed workload buckets instead of a single maximal-interference case:
   `other_card_only`, `same_card_only`, `mixed_cards`, `no_planned_budget`.
2. P-05 now outputs both full-limit baseline and tight-limit variant
   (`--p05-tight-preempt-limit`, default `5`).
3. Example:
   `python run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5`

## Scheduler Update (R17)
1. Mixed emergency preemption now uses a dual-resource synergy score:
   `score = mem_unit + gpu_unit + min(mem_unit, gpu_unit)` where each unit is capped to `1.0`.
2. This reduces one-sided victim bias under tight preemption budgets.

## Multi-Seed CI Update (R18)
1. Added repeated-run confidence summary mode:
   `--multi-seed-runs`, `--multi-seed-trials`, `--multi-seed-step`.
2. Example:
   `python run_advanced_research.py --trials 20000 --p05-tight-preempt-limit 5 --multi-seed-runs 7 --multi-seed-trials 5000 --multi-seed-step 9973`
3. Output now includes `multiseed.metrics` with mean/stddev/95% CI and per-seed rows.

## Real-Baseline Reliability Update (R19)
1. `run_advanced_research.py` now auto-plans weak real-baseline inputs to avoid invalid low-pressure runs:
   - raises too-short duration (`>=6s`)
   - raises too-small base memory by host memory tier
   - reduces over-large task count by safe-budget estimate
2. Dynamic stage now reports quality flags:
   - `low_signal_dynamic` (e.g., zero starts or no meaningful control events)
   - `emergency_signal_missing` (no emergency/preemption evidence in this run)
   - `cpu_clip_events` (experiment-only CPU view de-bias hits)
3. Real-baseline output includes planning metadata:
   - `planning_notes`, `host_total_mem_mb`
   - `predicted_no_scheduler_load_pct`, `predicted_fixed_worker_load_pct`

## Auto-Calibration GPU Extension (R19)
1. Scheduler runtime profiling now tracks process-level GPU memory peak when available (`nvidia-smi`).
2. Profile EMA now includes GPU (`ema_peak_gpu_mem_mb`).
3. Admission estimate auto-calibration can upgrade memory/CPU/GPU estimates together.

## Event-Targeted Real Baseline (R20)
1. New single-run retry mode:
   - `--real-target-eventful`
   - `--real-max-attempts`
   - `--real-attempt-seed-step`
2. It repeats real baseline attempts until dynamic evidence is not low-signal
   (or max attempts reached), and records each attempt trace.
3. Example:
   `python run_advanced_research.py --trials 200 --run-real-baseline --real-target-eventful --real-max-attempts 3 --real-task-count 8 --real-task-duration-sec 2 --real-base-mem-mb 96 --real-fixed-workers 4 --real-max-wall-sec 12`

## Eventful Threshold Tightening (R21)
1. Event-targeted attempts now also tighten scheduler thresholds by attempt index
   (not only workload parameters), to improve emergency/preempt trigger reliability.
2. Each attempt stores these dynamic threshold values in attempt trace outputs.

## Safety + Throughput Dual Target (R22)
1. Eventful mode can now require both:
   - safety evidence (`emergency/preempt`)
   - throughput evidence (`completed >= N`)
2. New CLI:
   - `--real-require-completion`
   - `--real-min-completed`
3. Retry trace includes:
   - `retry_reason` (`low_signal_dynamic` / `missing_emergency_signal` / `insufficient_completion` / `satisfied`)
   - per-attempt `max_scheduler_wall_sec` (auto-extended when completion is insufficient)

## Reason-Aware Retry Adaptation (R23)
1. Eventful retry now applies adaptive threshold bias:
   - `insufficient_completion` -> relax thresholds (`threshold_bias += 8`) and keep workload pressure.
   - `low_signal_dynamic` / `missing_emergency_signal` -> tighten thresholds (`threshold_bias -= 4`) and escalate workload pressure.
2. Attempt trace now includes:
   - `threshold_bias`
   - `adaptation_action` (`tighten_and_escalate` / `relax_and_hold` / `stop`)

## R24 Strong-Target Real Baseline
1. For stronger patent evidence (`completed >= 5`), use:
   `python run_advanced_research.py --trials 50 --run-real-baseline --real-target-eventful --real-require-completion --real-min-completed 5 --real-max-attempts 6 --real-task-count 8 --real-task-duration-sec 6 --real-base-mem-mb 2048 --real-fixed-workers 4 --real-max-wall-sec 24`
2. This run may auto-extend wall budget in retry branches and can take several minutes on real hardware.
3. Snapshot outputs are copied to `figures/*R24_completed_ge5*` for review stability.
