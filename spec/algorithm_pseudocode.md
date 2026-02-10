# 动态调度算法伪代码（与实现对齐版）

更新时间：2026-02-10（UTC+08:00）

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

  raw_snapshot <- monitor.sample()
  smoothed_snapshot <- ema_smooth(raw_snapshot)

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
    base_gpu_mb <- running_est_load.gpu_mb
  else:
    # real mode uses planned extra for same-tick yet-unobserved load
    base_mem_mb <- snapshot.memory_used_mb + planned_extra_load.mem_mb
    base_cpu_pct <- snapshot.cpu_percent + planned_extra_load.cpu_pct
    base_gpu_mb <- planned_extra_load.gpu_mb

  projected_mem_pct <- 100 * (base_mem_mb + task.estimated_mem_mb + cfg.reserve_memory_mb) / snapshot.memory_total_mb
  if projected_mem_pct >= cfg.memory_emergency_pct:
    return false, "projected memory emergency"

  projected_cpu_pct <- base_cpu_pct + task.estimated_cpu_percent
  if projected_cpu_pct >= cfg.cpu_hard_pct:
    return false, "projected cpu hard limit"

  if mode == HIGH and task.priority > cfg.high_mode_priority_cutoff:
    return false, "high mode blocks low-priority task"

  if cfg.enable_gpu_guard and snapshot.gpu_memory_total_mb != null and task.estimated_gpu_mem_mb > 0:
    projected_gpu_pct <- 100 * (snapshot.gpu_memory_used_mb + base_gpu_mb + task.estimated_gpu_mem_mb) / snapshot.gpu_memory_total_mb
    if projected_gpu_pct >= cfg.gpu_memory_emergency_pct:
      return false, "projected gpu memory emergency"

  return true, ""
```

## 5. 队列接纳（累计预算）
```text
function try_admit_tasks_with_cumulative_projection(...):
  planned_extra <- {mem_mb: 0, cpu_pct: 0, gpu_mb: 0}
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
      planned_extra.gpu_mb += task.estimated_gpu_mem_mb
    else:
      blocked_buffer.append((task, reason))

  push_back(blocked_buffer to pending_queue)
```

## 6. 紧急回收
```text
function preempt_low_priority_tasks(running_set, snapshot, cfg):
  candidates <- filter(running_set, preemptible == true)
  sort candidates by (priority desc, estimated_mem_mb desc, start_ts asc)
  k <- min(cfg.preempt_count_per_tick, len(candidates))

  reclaim_target_mb <- memory_target(snapshot, cfg)
  reclaimed_mb <- 0

  for i in [0 .. k-1]:
    ok <- stop_task(candidates[i], reason="PREEMPTED")
    if ok:
      reclaimed_mb += candidates[i].estimated_mem_mb
    if reclaimed_mb >= reclaim_target_mb:
      break
```

## 7. 停止任务（避免孤儿进程误判）
```text
function stop_task(task, reason):
  try terminate + wait
  if failed: try kill + wait
  if process still alive:
    emit TASK_STOP_FAILED
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
  preempted_total
  failed_total
  timeout_total
  emergency_ticks
```
