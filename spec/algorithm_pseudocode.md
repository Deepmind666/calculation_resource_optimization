# 动态调度算法伪代码（与实现对齐版）

更新时间：2026-02-11（UTC+08:00）

## 1. 调度主循环
```text
INPUT:
  pending_queue
  running_set
  scheduler_config
  previous_mode
  emergency_cooldown_left

LOOP every check_interval_sec:
  refresh_running_tasks(running_set)
  # in real-run mode: sample process RSS/CPU peaks and update profile buffers

  raw_snapshot <- monitor.sample()
  smoothed_snapshot <- ema_smooth(raw_snapshot)
  # preserve per-card GPU metadata for affinity admission path
  smoothed_snapshot.gpu_cards <- raw_snapshot.gpu_cards (or previous if raw missing)

  mode <- evaluate_mode(
    raw_snapshot,
    smoothed_snapshot,
    scheduler_config,
    previous_mode,
    emergency_cooldown_left
  )

  if mode == EMERGENCY:
    preempt_low_priority_tasks(running_set, smoothed_snapshot, scheduler_config)

  target_workers <- compute_target_workers(mode, scheduler_config)
  start_budget <- compute_start_budget(mode, scheduler_config)

  try_admit_tasks_with_cumulative_projection(
    pending_queue,
    running_set,
    smoothed_snapshot,
    mode,
    target_workers,
    start_budget,
    scheduler_config
  )

  emit_tick_report()
  previous_mode <- mode
END LOOP
```

## 2. 模式判定（紧急看 raw，稳态看 smooth）
```text
function evaluate_mode(raw, smooth, cfg, previous_mode, cooldown_left):
  # Emergency: must react immediately to raw spikes.
  if raw.memory_percent >= cfg.memory_emergency_pct:
    cooldown_left <- cfg.emergency_cooldown_ticks
    return EMERGENCY
  if raw.swap_percent >= cfg.swap_emergency_pct:
    cooldown_left <- cfg.emergency_cooldown_ticks
    return EMERGENCY
  if raw.memory_available_mb <= cfg.reserve_memory_mb:
    cooldown_left <- cfg.emergency_cooldown_ticks
    return EMERGENCY
  if cfg.enable_gpu_guard and raw.gpu_memory_percent != null and
     raw.gpu_memory_percent >= cfg.gpu_memory_emergency_pct:
    cooldown_left <- cfg.emergency_cooldown_ticks
    return EMERGENCY

  # Cooldown: keep EMERGENCY for extra ticks after trigger disappears.
  if previous_mode == EMERGENCY and cooldown_left > 0:
    cooldown_left <- cooldown_left - 1
    return EMERGENCY

  # HIGH/NORMAL switching uses smoothed values + hysteresis.
  if smooth.memory_percent >= cfg.memory_high_pct:
    return HIGH
  if smooth.cpu_percent >= cfg.cpu_high_pct:
    return HIGH
  if cfg.enable_gpu_guard and smooth.gpu_memory_percent != null and
     smooth.gpu_memory_percent >= cfg.gpu_memory_high_pct:
    return HIGH

  if previous_mode == HIGH and
     (smooth.memory_percent > cfg.memory_high_pct - cfg.mode_hysteresis_pct or
      smooth.cpu_percent > cfg.cpu_high_pct - cfg.mode_hysteresis_pct or
      (cfg.enable_gpu_guard and smooth.gpu_memory_percent != null and
       smooth.gpu_memory_percent > cfg.gpu_memory_high_pct - cfg.mode_hysteresis_pct)):
    return HIGH

  return NORMAL
```

## 3. 目标并发与启动节流
```text
function compute_target_workers(mode, cfg):
  if mode == NORMAL:
    return cfg.max_workers
  if mode == HIGH:
    return max(cfg.min_workers, floor(cfg.max_workers / 2))
  return 0  # EMERGENCY

function compute_start_budget(mode, cfg):
  if mode == NORMAL:
    return cfg.max_start_per_tick_normal
  if mode == HIGH:
    return cfg.max_start_per_tick_high
  return 0
```

## 4. 接纳控制（修复 dry_run 双计数）
```text
function can_admit(
  task, snapshot, mode, cfg,
  running_est_load, planned_extra_load
):
  if mode == EMERGENCY:
    return false, "emergency mode"

  if cfg.dry_run:
    # running_set already includes tasks started earlier in this tick
    # so DO NOT add planned_extra_load again.
    base_mem_mb <- snapshot.memory_used_mb + running_est_load.mem_mb
    base_cpu_pct <- snapshot.cpu_percent + running_est_load.cpu_pct
    base_gpu_mb <- running_gpu_load.unbound_mb
  else:
    # real mode uses planned extra for same-tick yet-unobserved load
    base_mem_mb <- snapshot.memory_used_mb + planned_extra_load.mem_mb
    base_cpu_pct <- snapshot.cpu_percent + planned_extra_load.cpu_pct
    base_gpu_mb <- planned_extra_load.gpu_unbound_mb

  projected_mem_pct <- 100 * (base_mem_mb + task.estimated_mem_mb + cfg.reserve_memory_mb) / snapshot.memory_total_mb
  if projected_mem_pct >= cfg.memory_emergency_pct:
    return false, "projected memory emergency"

  projected_cpu_pct <- base_cpu_pct + task.estimated_cpu_percent
  if projected_cpu_pct >= cfg.cpu_hard_pct:
    return false, "projected cpu hard limit"

  if mode == HIGH and task.priority > cfg.high_mode_priority_cutoff:
    return false, "high mode blocks low-priority task"

  if cfg.enable_gpu_guard and task.estimated_gpu_mem_mb > 0:
    if task.target_gpu_index != null:
      if snapshot.gpu_cards is null or task.target_gpu_index out of range:
        return false, "target gpu unavailable"
      gpu_used_mb <- snapshot.gpu_cards[task.target_gpu_index].used_mb
      gpu_total_mb <- snapshot.gpu_cards[task.target_gpu_index].total_mb
      if cfg.dry_run:
        base_gpu_mb <- base_gpu_mb + running_gpu_load.by_index[task.target_gpu_index]
      else:
        base_gpu_mb <- base_gpu_mb + planned_extra_load.gpu_by_index[task.target_gpu_index]
    else:
      gpu_used_mb <- snapshot.gpu_memory_used_mb
      gpu_total_mb <- snapshot.gpu_memory_total_mb
      if cfg.dry_run:
        base_gpu_mb <- base_gpu_mb + sum(running_gpu_load.by_index.values)
      else:
        base_gpu_mb <- base_gpu_mb + sum(planned_extra_load.gpu_by_index.values)

    if gpu_used_mb != null and gpu_total_mb != null:
      projected_gpu_pct <- 100 * (gpu_used_mb + base_gpu_mb + task.estimated_gpu_mem_mb) / gpu_total_mb
    else:
      projected_gpu_pct <- null

  if projected_gpu_pct != null:
    if projected_gpu_pct >= cfg.gpu_memory_emergency_pct:
      return false, "projected gpu memory emergency"

  return true, ""
```

## 5. 队列接纳（累计预算）
```text
function try_admit_tasks_with_cumulative_projection(...):
  planned_extra <- {
    mem_mb: 0,
    cpu_pct: 0,
    gpu_unbound_mb: 0,
    gpu_by_index: {}
  }
  if cfg.dry_run:
    running_est_load <- estimate_running_once(running_set)
    running_gpu_load <- estimate_running_gpu_once(running_set)
  attempts <- len(pending_queue)
  blocked_buffer <- []

  for i in [1 .. attempts]:
    if running_count >= target_workers: break
    if started_count >= start_budget: break

    task <- pop_highest_priority(pending_queue)
    ok, reason <- can_admit(task, snapshot, mode, cfg, running_est_load, planned_extra)

    if ok:
      start_task(task)
      planned_extra.mem_mb += task.estimated_mem_mb
      planned_extra.cpu_pct += task.estimated_cpu_percent
      if cfg.dry_run:
        running_est_load.mem_mb += task.estimated_mem_mb
        running_est_load.cpu_pct += task.estimated_cpu_percent
      if task.target_gpu_index == null:
        planned_extra.gpu_unbound_mb += task.estimated_gpu_mem_mb
        if cfg.dry_run:
          running_gpu_load.unbound_mb += task.estimated_gpu_mem_mb
      else:
        planned_extra.gpu_by_index[task.target_gpu_index] += task.estimated_gpu_mem_mb
        if cfg.dry_run:
          running_gpu_load.by_index[task.target_gpu_index] += task.estimated_gpu_mem_mb
    else:
      blocked_buffer.append((task, reason))

  push_back(blocked_buffer to pending_queue)
```

## 6. 紧急回收
```text
function preempt_low_priority_tasks(running_set, snapshot, raw_snapshot, cfg):
  emergency_view <- raw_snapshot if raw_snapshot != null else snapshot
  candidates <- filter(running_set, preemptible == true)
  memory_emergency <- (
    emergency_view.memory_percent >= cfg.memory_emergency_pct or
    emergency_view.swap_percent >= cfg.swap_emergency_pct or
    emergency_view.memory_available_mb <= cfg.reserve_memory_mb
  )
  gpu_emergency <- (
    cfg.enable_gpu_guard and
    emergency_view.gpu_memory_percent != null and
    emergency_view.gpu_memory_percent >= cfg.gpu_memory_emergency_pct
  )
  hottest_gpu_index <- max_gpu_memory_percent_card(emergency_view.gpu_cards or snapshot.gpu_cards)

  reclaim_needed_mem_mb <- memory_reclaim_target(emergency_view, snapshot.memory_total_mb, cfg)
  reclaim_needed_gpu_mb <- gpu_reclaim_target(emergency_view, cfg)  # 0 if no gpu emergency
  if raw_snapshot != null and not memory_emergency and not gpu_emergency:
    return []  # emergency cooldown without active emergency dimension

  mem_denom <- max(1.0, reclaim_needed_mem_mb)
  gpu_denom <- max(1.0, reclaim_needed_gpu_mb)

  sort candidates by (
    priority desc,
    normalized_reclaim_score(
      mem_component = (estimated_mem_mb / mem_denom) when (memory_emergency or not gpu_emergency),
      gpu_component = (effective_gpu_reclaim / gpu_denom) when gpu_emergency
    ) desc,
    age_order_by_preempt_sort_key
  )
  k <- min(cfg.preempt_count_per_tick, len(candidates))

  reclaimed_mem_mb <- 0
  reclaimed_gpu_mb <- 0

  for i in [0 .. k-1]:
    ok <- stop_task(candidates[i], reason="PREEMPTED")
    removed <- candidates[i] no longer in running_set
    if ok or removed:
      reclaimed_mem_mb += candidates[i].estimated_mem_mb
      reclaimed_gpu_mb += effective_gpu_reclaim(candidates[i], gpu_emergency, hottest_gpu_index)
    if reclaimed_mem_mb >= reclaim_needed_mem_mb and reclaimed_gpu_mb >= reclaim_needed_gpu_mb:
      break
```

## 7. 停止任务（避免孤儿进程误判）
```text
function stop_task(task, reason):
  try terminate + wait
  if failed: try kill + wait
  if process still alive:
    if first_failure:
      remember stop_requested_ts
    emit TASK_STOP_FAILED(elapsed_sec)
    if elapsed_sec >= cfg.stuck_task_timeout_sec:
      force remove task from running_set
      update metrics for forced PREEMPTED/TIMEOUT
      emit TASK_STUCK_REMOVED
    return false

  remove task from running_set
  update metrics for PREEMPTED/TIMEOUT
  emit TASK_STOPPED
  return true
```

## 8. GPU 监控（多卡）
```text
function sample_gpu():
  rows <- parse nvidia-smi rows (util, used, total)
  if rows empty: return {}
  choose row with max(used/total) as riskiest card
  return util, memory_used_mb, memory_total_mb, memory_percent
```

## 9. 指标输出
```text
metrics:
  submitted_total
  started_total
  completed_total
  blocked_total            # blocked events count
  blocked_task_total       # unique blocked task count
  preempted_total
  failed_total
  timeout_total
  stuck_removed_total
  emergency_ticks
```

## 10. 估算自校准（R15）
```text
function apply_estimation_profile(task, cfg, profile_store):
  if not cfg.enable_estimation_autocalibration:
    return task
  key <- task.profile_key or first_command_token(task.command) or "task:" + task.task_id
  profile <- profile_store[key]
  if profile missing or profile.samples < cfg.profile_min_samples:
    return task(with profile_key=key)

  calibrated_mem <- max(task.estimated_mem_mb, profile.ema_peak_mem_mb * cfg.profile_safety_multiplier)
  calibrated_cpu <- max(task.estimated_cpu_percent, profile.ema_peak_cpu_pct * cfg.profile_safety_multiplier)
  calibrated_gpu <- max(task.estimated_gpu_mem_mb, profile.ema_peak_gpu_mem_mb * cfg.profile_safety_multiplier)
  emit TASK_ESTIMATE_CALIBRATED(before, after, profile.samples)
  return task(with upgraded estimates and profile_key=key)

function update_profile_from_runtime(runtime, cfg, profile_store):
  if not cfg.enable_estimation_autocalibration:
    return
  if runtime.observed_peak_mem_mb <= 0 and runtime.observed_peak_cpu_pct <= 0 and runtime.observed_peak_gpu_mem_mb <= 0:
    return
  key <- runtime.profile_key or derive_profile_key(runtime.spec)
  profile <- profile_store.get_or_create(key)
  profile.ema_peak_mem_mb <- EMA(profile.ema_peak_mem_mb, runtime.observed_peak_mem_mb, cfg.profile_ema_alpha)
  profile.ema_peak_cpu_pct <- EMA(profile.ema_peak_cpu_pct, runtime.observed_peak_cpu_pct, cfg.profile_ema_alpha)
  profile.ema_peak_gpu_mem_mb <- EMA(profile.ema_peak_gpu_mem_mb, runtime.observed_peak_gpu_mem_mb, cfg.profile_ema_alpha)
  profile.samples += 1
  emit TASK_PROFILE_UPDATED(key, samples, ema_peak_mem_mb, ema_peak_cpu_pct, ema_peak_gpu_mem_mb)
```

## R17 Update: Mixed-Emergency Preemption Scoring
When both memory and GPU are emergency bottlenecks in the same tick:
1. Compute normalized reclaim ratios per candidate runtime:
   - `mem_norm = estimated_mem_mb / reclaim_needed_mem_mb`
   - `gpu_norm = effective_gpu_reclaim / reclaim_needed_gpu_mb`
2. Cap each dimension to avoid one-sided overflow domination:
   - `mem_unit = min(1.0, mem_norm)`
   - `gpu_unit = min(1.0, gpu_norm)`
3. Use dual-resource synergy score:
   - `score = mem_unit + gpu_unit + min(mem_unit, gpu_unit)`
4. Keep existing priority and age ordering as secondary tie-breakers.

## R19 Update: Real-Baseline Validity Gate
```text
function plan_real_baseline_params(task_count, duration_sec, base_mem_mb, fixed_workers, host_total_mem_mb):
  duration_sec <- max(duration_sec, 6.0)
  min_task_count <- max(4, fixed_workers + 1)
  task_count <- max(task_count, min_task_count)

  if host_total_mem_mb >= 16384:
    base_floor_mb <- 2048
  else if host_total_mem_mb >= 8192:
    base_floor_mb <- 1024
  else:
    base_floor_mb <- 512
  base_mem_mb <- max(base_mem_mb, base_floor_mb)

  avg_runtime_factor <- 1.3
  max_tasks_by_safe_budget <- floor(0.90 * host_total_mem_mb / (base_mem_mb * avg_runtime_factor))
  if max_tasks_by_safe_budget >= min_task_count:
    task_count <- min(task_count, max_tasks_by_safe_budget)
  else:
    base_mem_mb <- floor(0.90 * host_total_mem_mb / (min_task_count * avg_runtime_factor))

  return adjusted(task_count, duration_sec, base_mem_mb)

function validate_real_baseline_output(dynamic_result):
  assert dynamic_result has fields:
    blocked_event_total, preempted_total, emergency_ticks, scheduler_timeout_hit
  assert dynamic_result has quality flags:
    low_signal_dynamic, emergency_signal_missing, cpu_clip_events
  if emergency_ticks == 0 and preempted_total == 0 and blocked_event_total == 0:
    mark low_signal=true and report recommendation for stronger pressure
  # GPU peak sanity: invalid totals / absurd percentages must be filtered
  # valid range for reported peak_gpu_memory_pct is [0, 100]
```

## R20 Update: Event-Targeted Real-Baseline Retry
```text
function need_eventful_retry(dynamic_result, require_completion=false, min_completed=1):
  if dynamic_result.low_signal_dynamic == 1:
    return true, "low_signal_dynamic"
  if dynamic_result.emergency_signal_missing == 1:
    return true, "missing_emergency_signal"
  if require_completion and dynamic_result.completed < min_completed:
    return true, "insufficient_completion"
  return false, "satisfied"

function apply_eventful_threshold_bias(base_cfg, threshold_bias):
  memory_high <- clamp(base_cfg.memory_high_pct + threshold_bias, 50.0, 98.0)
  memory_emergency <- clamp(base_cfg.memory_emergency_pct + threshold_bias, memory_high + 1.0, 99.0)
  return cfg(
    memory_high_pct=memory_high,
    memory_emergency_pct=memory_emergency,
    preempt_count_per_tick=base_cfg.preempt_count_per_tick,
    cpu_high_pct=base_cfg.cpu_high_pct,
    cpu_hard_pct=base_cfg.cpu_hard_pct
  )

function update_eventful_threshold_bias(current_bias, reason):
  if reason == "insufficient_completion":
    return min(20.0, current_bias + 8.0)      # relax to restore throughput
  if reason in {"low_signal_dynamic", "missing_emergency_signal", "missing_dynamic_row"}:
    return max(-20.0, current_bias - 4.0)     # tighten to improve emergency observability
  return current_bias

function escalate_real_baseline_params(task_count, duration_sec, base_mem_mb, fixed_workers, host_total_mem_mb):
  next_duration <- min(20.0, duration_sec + 2.0)
  next_base_mem <- ceil(base_mem_mb * 1.25)
  next_task_count <- task_count + max(2, fixed_workers // 2)
  return plan_real_baseline_params(
    task_count=next_task_count,
    duration_sec=next_duration,
    base_mem_mb=next_base_mem,
    fixed_workers=fixed_workers,
    host_total_mem_mb=host_total_mem_mb
  )

function run_real_baseline_until_eventful(max_attempts, require_completion=false, min_completed=1):
  params <- plan_real_baseline_params(initial_inputs)
  attempts <- []
  wall_budget <- initial_wall_budget
  threshold_bias <- 0.0
  for i in [1 .. max_attempts]:
    base_dynamic_cfg <- plan_eventful_scheduler_thresholds(i-1)
    dynamic_cfg <- apply_eventful_threshold_bias(base_dynamic_cfg, threshold_bias)
    result <- run_real_machine_baseline(params, dynamic_cfg, wall_budget)
    dynamic <- find mode C_dynamic_scheduler from result
    retry_needed, reason <- need_eventful_retry(dynamic, require_completion, min_completed)
    append (params, dynamic_summary, reason, threshold_bias, dynamic_cfg) to attempts
    if not retry_needed:
      break
    if reason == "insufficient_completion":
      wall_budget <- min(120, wall_budget + 8)   # give admitted tasks time to complete
      # keep workload pressure unchanged in this branch to avoid amplifying starvation
    else:
      params <- escalate_real_baseline_params(params, result.host_total_mem_mb)
    threshold_bias <- update_eventful_threshold_bias(threshold_bias, reason)
  return final_result_with_attempt_trace(attempts)

function plan_eventful_scheduler_thresholds(attempt_index):
  # tighten memory thresholds with attempt index to improve emergency/preempt observability
  memory_high_pct <- max(60, 76 - 5*attempt_index)
  memory_emergency_pct <- max(memory_high_pct + 4, 82 - 6*attempt_index)
  preempt_count_per_tick <- 1 + floor(attempt_index / 2)
  cpu_high_pct <- 99.9
  cpu_hard_pct <- 100.0
  return config(memory_high_pct, memory_emergency_pct, preempt_count_per_tick, cpu_high_pct, cpu_hard_pct)
```
