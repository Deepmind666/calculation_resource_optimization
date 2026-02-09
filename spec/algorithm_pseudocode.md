# 动态调度伪代码（资源优化主线）

更新时间：2026-02-09（UTC+08:00）

## 1. 调度主循环

```text
INPUT:
  pending_queue
  running_set
  scheduler_config

LOOP every check_interval_sec:
  raw_snapshot <- monitor.sample()
  snapshot <- smooth(raw_snapshot, ema_alpha)
  refresh_running_tasks(running_set)
  mode <- evaluate_mode(snapshot, scheduler_config)

  if mode == EMERGENCY:
      preempt_low_priority_tasks(running_set, scheduler_config)

  target_workers <- compute_target_workers(mode, scheduler_config)
  try_admit_tasks_with_cumulative_projection(
      pending_queue, running_set, snapshot, target_workers, scheduler_config
  )

  emit_tick_report(snapshot, mode, running_set, pending_queue)
END LOOP
```

---

## 2. 模式判定

```text
function evaluate_mode(snapshot, cfg):
  if snapshot.memory_percent >= cfg.memory_emergency_pct:
      return EMERGENCY
  if snapshot.swap_percent >= cfg.swap_emergency_pct:
      return EMERGENCY
  if cfg.enable_gpu_guard and snapshot.gpu_memory_percent != null and
     snapshot.gpu_memory_percent >= cfg.gpu_memory_emergency_pct:
      return EMERGENCY

  if snapshot.memory_percent >= cfg.memory_high_pct:
      return HIGH
  if snapshot.cpu_percent >= cfg.cpu_high_pct:
      return HIGH
  if cfg.enable_gpu_guard and snapshot.gpu_memory_percent != null and
     snapshot.gpu_memory_percent >= cfg.gpu_memory_high_pct:
      return HIGH

  return NORMAL
```

---

## 3. 目标并发计算

```text
function compute_target_workers(mode, cfg):
  if mode == NORMAL:
      return cfg.max_workers
  if mode == HIGH:
      return max(cfg.min_workers, floor(cfg.max_workers / 2))
  return 0   # EMERGENCY
```

---

## 4. 接纳控制

```text
function can_admit(task, snapshot, mode, cfg):
  if mode == EMERGENCY:
      return false, "emergency mode"

  projected_mem_mb = snapshot.memory_used_mb + task.estimated_mem_mb + cfg.reserve_memory_mb
  projected_mem_pct = 100 * projected_mem_mb / snapshot.memory_total_mb
  if projected_mem_pct >= cfg.memory_emergency_pct:
      return false, "projected memory emergency"

  projected_cpu_pct = snapshot.cpu_percent + task.estimated_cpu_percent
  if projected_cpu_pct >= cfg.cpu_hard_pct:
      return false, "projected cpu hard limit"

  if mode == HIGH and task.priority > cfg.high_mode_priority_cutoff:
      return false, "blocked low-priority task in high mode"

  if cfg.enable_gpu_guard and snapshot.gpu_memory_total_mb != null:
      projected_gpu_mb = snapshot.gpu_memory_used_mb + task.estimated_gpu_mem_mb
      projected_gpu_pct = 100 * projected_gpu_mb / snapshot.gpu_memory_total_mb
      if projected_gpu_pct >= cfg.gpu_memory_emergency_pct:
          return false, "projected gpu memory emergency"

  return true, ""
```

---

## 5. 紧急回收

```text
function preempt_low_priority_tasks(running_set, cfg):
  candidates = filter(running_set, task.preemptible == true)
  sort candidates by priority descending  # 数值越大优先级越低
  k = min(cfg.preempt_count_per_tick, len(candidates))
  for i in [0 .. k-1]:
      terminate(candidates[i], reason="emergency preemption")
```

---

## 6. 尝试接纳任务

```text
function try_admit_tasks(queue, running_set, snapshot, target_workers, cfg):
  capacity = target_workers - len(running_set)
  if capacity <= 0:
      return

  planned_mem_extra = 0
  planned_cpu_extra = 0
  planned_gpu_extra = 0

  trial_count = len(queue)
  blocked_buffer = []
  for i in [1 .. trial_count]:
      if len(running_set) >= target_workers:
          break

      task = pop_highest_priority(queue)
      ok, reason = can_admit(
          task, snapshot, current_mode, cfg,
          planned_mem_extra, planned_cpu_extra, planned_gpu_extra
      )
      if ok:
          start_task(task)
          add running_set
          planned_mem_extra += task.estimated_mem_mb
          planned_cpu_extra += task.estimated_cpu_percent
          planned_gpu_extra += task.estimated_gpu_mem_mb
      else:
          blocked_buffer.append((task, reason))

  push_back(blocked_buffer to queue)
```

---

## 7. 任务刷新

```text
function refresh_running_tasks(running_set):
  for task in running_set:
      if task.finished():
          mark COMPLETED and remove from running_set
      else if runtime(task) > task.max_runtime_sec:
          terminate(task, reason="timeout")
```

---

## 8. 指标输出

```text
metrics:
  submitted_total
  started_total
  completed_total
  blocked_total
  preempted_total
  emergency_ticks
```
  if previous_mode == EMERGENCY and cooldown_left > 0:
      cooldown_left -= 1
      return EMERGENCY
