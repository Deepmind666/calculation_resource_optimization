# 数据模型（与当前实现一致）

更新时间：2026-02-10（UTC+08:00）

## 1. ResourceSnapshot
```python
@dataclass
class ResourceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    memory_available_mb: float
    swap_percent: float
    gpu_util_percent: Optional[float] = None
    gpu_memory_percent: Optional[float] = None
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
```

用途：
1. 描述每个调度 tick 的资源快照。
2. 作为模式判定与准入计算的输入。

## 2. TaskSpec
```python
@dataclass
class TaskSpec:
    task_id: str
    command: List[str]
    priority: int
    estimated_mem_mb: int
    estimated_cpu_percent: float
    estimated_gpu_mem_mb: int = 0
    preemptible: bool = True
    max_runtime_sec: float = 300.0
    dry_run_ticks: int = 2
```

关键约束：
1. `task_id` 必须唯一且非空。
2. `priority` 必须为 `>=1` 的整数，值越小优先级越高。
3. 资源估值必须 `>=0`。

## 3. SchedulerConfig
```python
@dataclass
class SchedulerConfig:
    max_workers: int = 4
    min_workers: int = 1
    check_interval_sec: float = 0.5

    memory_high_pct: float = 85.0
    memory_emergency_pct: float = 92.0
    cpu_high_pct: float = 80.0
    cpu_hard_pct: float = 95.0
    swap_emergency_pct: float = 80.0

    enable_gpu_guard: bool = True
    gpu_memory_high_pct: float = 85.0
    gpu_memory_emergency_pct: float = 95.0

    reserve_memory_mb: int = 512
    high_mode_priority_cutoff: int = 3
    preempt_count_per_tick: int = 1
    kill_timeout_sec: float = 3.0
    mode_hysteresis_pct: float = 3.0
    emergency_cooldown_ticks: int = 2
    ema_alpha: float = 0.6
    max_start_per_tick_normal: int = 4
    max_start_per_tick_high: int = 1
    dry_run: bool = False
    max_event_log_entries: int = 5000
```

关键约束：
1. worker 范围合法：`min_workers >= 1` 且 `max_workers >= min_workers`。
2. 阈值合法：`memory_high < memory_emergency`，`cpu_high < cpu_hard`。
3. 采样/终止超时、日志上限等参数必须为正值。

## 4. TaskRuntime
```python
@dataclass
class TaskRuntime:
    spec: TaskSpec
    start_ts: float
    state: str
    process: Optional[subprocess.Popen] = None
    remaining_ticks: int = 0
```

说明：
1. `dry_run=True` 时用 `remaining_ticks` 驱动任务结束。
2. 真实进程模式下，`process` 负责状态轮询与终止。

## 5. SchedulerMetrics
```python
@dataclass
class SchedulerMetrics:
    submitted_total: int = 0
    started_total: int = 0
    completed_total: int = 0
    blocked_total: int = 0
    preempted_total: int = 0
    failed_total: int = 0
    timeout_total: int = 0
    emergency_ticks: int = 0
```

说明：
1. `blocked_total` 是阻断事件次数，不是唯一任务数。
2. 唯一阻断任务数由实验脚本派生 `unique_blocked_tasks`。

## 6. TickReport
```python
@dataclass
class TickReport:
    tick_id: int
    mode: str
    started: List[str]
    blocked: List[Dict[str, str]]
    preempted: List[str]
    running_count: int
    pending_count: int
    snapshot: ResourceSnapshot
```

说明：
1. `mode` 取值：`NORMAL/HIGH/EMERGENCY`。
2. 是每轮调度的可审计输出单元。
