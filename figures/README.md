# figures

本目录存放资源调度实验输出：
1. `scheduler_demo_report.json`：单次演示运行的 tick 报告。
2. `scheduler_experiment_metrics.csv`：多场景指标表。
3. `scheduler_experiment_metrics.json`：多场景指标明细。
4. `patent_evidence_metrics.csv` / `.json`：P-02/P-03 消融证据。
5. `advanced_research_metrics.csv` / `.json`：P-04/P-05 大规模消融与真机基线对比结果。

## Advanced Metrics (R16)
- `advanced_research_metrics.json` now includes `p04.scenario_breakdown` for stratified analysis.
- `p05` includes both full-limit metrics and tight-limit metrics (`*_tight`) to stress victim-selection quality.

## R18 Multi-Seed Output
- `advanced_research_metrics.json` now optionally includes `multiseed`:
  - `metrics`: mean/stddev/ci95_low/ci95_high/min/max for key metrics
  - `per_seed`: traceable values for each seed run
- CSV includes `MULTI-SEED-CI` rows for reviewer-friendly import.

## R19 Real-Baseline Fields
- `real_baseline` now includes planning metadata:
  - `planning_notes`, `host_total_mem_mb`
  - `predicted_no_scheduler_load_pct`, `predicted_fixed_worker_load_pct`
- `C_dynamic_scheduler` rows now include experiment-quality flags:
  - `started_total`
  - `low_signal_dynamic`
  - `emergency_signal_missing`
  - `cpu_clip_events`
- Multi-run summary rows (`REAL-BASELINE-CI`) include CI stats for these additional metrics.

## R20 Eventful Retry Output
- `advanced_research_metrics.json` may include `real_baseline_eventful`:
  - `max_attempts`, `attempts_executed`, `eventful_achieved`
  - `attempts[]` with per-attempt params + dynamic summary
  - `final_result` as the final baseline payload
- CSV includes `REAL-BASELINE-ATTEMPT` rows for each attempt.

## R21 Attempt Threshold Fields
- `REAL-BASELINE-ATTEMPT` rows now include:
  - `dynamic_memory_high_pct`
  - `dynamic_memory_emergency_pct`
  - `dynamic_preempt_count_per_tick`
- These fields provide reproducible evidence for event-trigger strategy across attempts.

## R22 Dual-Target Fields
- `REAL-BASELINE-ATTEMPT` rows now additionally include:
  - `completed`
  - `retry_reason`
  - `max_scheduler_wall_sec`
- For dual-target runs (`--real-require-completion`), these fields explain why retries continue or stop.

## R23 Retry Adaptation Fields
- REAL-BASELINE-ATTEMPT rows now additionally include:
  - threshold_bias
  - adaptation_action
- These fields make reason-aware retry actions auditable across attempts.

## R24 Strong Evidence Snapshot
- Added immutable snapshot files for `min_completed=5` dual-target run:
  - `advanced_research_metrics_R24_completed_ge5_2026-02-13.json`
  - `advanced_research_metrics_R24_completed_ge5_2026-02-13.csv`
  - `real_baseline_eventful_R24_summary_2026-02-13.json`
  - `real_baseline_eventful_R24_summary_2026-02-13.csv`
- Key outcome in snapshot: `eventful_achieved=1`, `final_completed=7`, `final_emergency_ticks=3`, `final_preempted_total=1`.
