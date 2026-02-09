# 数据模型（资源调度主线）

更新时间：2026-02-09（UTC+08:00）

## 1. ResourceSnapshot（资源快照）

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
    gpu_util_percent: Optional[float]
    gpu_memory_percent: Optional[float]
    gpu_memory_used_mb: Optional[float]
    gpu_memory_total_mb: Optional[float]
```

用途：
1. 每个调度周期的实时输入。
2. 模式判定（NORMAL/HIGH/EMERGENCY）依据。

---

## 2. TaskSpec（任务定义）

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

字段说明：
1. `priority`：越小越重要。
2. `estimated_mem_mb`：用于接纳前预测，防止冲过内存上限。
3. `preemptible`：紧急时是否允许被终止。

---

## 3. SchedulerConfig（调度配置）

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

    dry_run: bool = False
```

---

## 4. TaskRuntime（运行时状态）

```python
@dataclass
class TaskRuntime:
    spec: TaskSpec
    start_ts: float
    state: str
    process: Optional[subprocess.Popen] = None
    remaining_ticks: int = 0
```

状态举例：
1. `RUNNING`
2. `COMPLETED`
3. `PREEMPTED`
4. `FAILED`
5. `TIMEOUT`

---

## 5. TickReport（单次调度报告）

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

---

## 6. Metrics（累计指标）

```python
@dataclass
class SchedulerMetrics:
    submitted_total: int = 0
    started_total: int = 0
    completed_total: int = 0
    blocked_total: int = 0
    preempted_total: int = 0
    failed_total: int = 0
    emergency_ticks: int = 0
```

---

## 7. 关系总览
1. `ResourceSnapshot` 决定当前模式。
2. `TaskSpec` 决定任务是否允许启动。
3. `SchedulerConfig` 决定阈值、并发和保护策略。
4. `TaskRuntime` 反映当前执行状态。
5. `TickReport` 和 `Metrics` 用于审计与调优。
