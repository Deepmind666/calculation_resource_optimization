# 鏁版嵁妯″瀷锛堜笌褰撳墠瀹炵幇涓€鑷达級

鏇存柊鏃堕棿锛?026-02-11锛圲TC+08:00锛?
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
    gpu_cards: Optional[List[Dict[str, float]]] = None
```

鐢ㄩ€旓細
1. 鎻忚堪姣忎釜璋冨害 tick 鐨勮祫婧愬揩鐓с€?2. 浣滀负妯″紡鍒ゅ畾涓庡噯鍏ヨ绠楃殑杈撳叆銆?
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
    target_gpu_index: Optional[int] = None
    profile_key: Optional[str] = None
    preemptible: bool = True
    max_runtime_sec: float = 300.0
    dry_run_ticks: int = 2
```

鍏抽敭绾︽潫锛?1. `task_id` 蹇呴』鍞竴涓旈潪绌恒€?2. `priority` 蹇呴』涓?`>=1` 鐨勬暣鏁帮紝鍊艰秺灏忎紭鍏堢骇瓒婇珮銆?3. 璧勬簮浼板€煎繀椤?`>=0`銆?
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
    preempt_sort_key: str = "oldest_first"
    kill_timeout_sec: float = 3.0
    stuck_task_timeout_sec: float = 30.0
    mode_hysteresis_pct: float = 3.0
    emergency_cooldown_ticks: int = 2
    ema_alpha: float = 0.6
    max_start_per_tick_normal: int = 4
    max_start_per_tick_high: int = 1
    dry_run: bool = False
    max_event_log_entries: int = 5000
    enable_estimation_autocalibration: bool = False
    profile_ema_alpha: float = 0.5
    profile_safety_multiplier: float = 1.25
    profile_min_samples: int = 3
    runtime_sample_interval_sec: float = 0.2
    max_resource_profiles: int = 1024
```

鍏抽敭绾︽潫锛?1. worker 鑼冨洿鍚堟硶锛歚min_workers >= 1` 涓?`max_workers >= min_workers`銆?2. 闃堝€煎悎娉曪細`memory_high < memory_emergency`锛宍cpu_high < cpu_hard`銆?3. 閲囨牱/缁堟瓒呮椂銆佹棩蹇椾笂闄愮瓑鍙傛暟蹇呴』涓烘鍊笺€?
## 4. TaskRuntime
```python
@dataclass
class TaskRuntime:
    spec: TaskSpec
    start_ts: float
    state: str
    process: Optional[subprocess.Popen] = None
    remaining_ticks: int = 0
    stop_requested_ts: Optional[float] = None
    stop_reason: Optional[str] = None
    profile_key: Optional[str] = None
    observed_peak_mem_mb: float = 0.0
    observed_peak_cpu_pct: float = 0.0
    observed_peak_gpu_mem_mb: float = 0.0
    last_sample_ts: float = 0.0
    ps_process: Optional[Any] = None
```

璇存槑锛?1. `dry_run=True` 鏃剁敤 `remaining_ticks` 椹卞姩浠诲姟缁撴潫銆?2. 鐪熷疄杩涚▼妯″紡涓嬶紝`process` 璐熻矗鐘舵€佽疆璇笌缁堟銆?
## 4.1 ResourceProfile
```python
@dataclass
class ResourceProfile:
    samples: int = 0
    ema_peak_mem_mb: float = 0.0
    ema_peak_cpu_pct: float = 0.0
    ema_peak_gpu_mem_mb: float = 0.0
    last_updated_ts: float = 0.0
```

璇存槑锛?1. 鎸?`profile_key` 鑱氬悎浠诲姟鍘嗗彶宄板€肩敾鍍忋€?2. 鏂颁换鍔℃彁浜ゆ椂鍙熀浜?EMA 鐢诲儚鍋氫繚瀹堟斁澶э紝闄嶄綆浼扮畻鍋忓皬椋庨櫓銆?
## 5. SchedulerMetrics
```python
@dataclass
class SchedulerMetrics:
    submitted_total: int = 0
    started_total: int = 0
    completed_total: int = 0
    blocked_total: int = 0
    blocked_task_total: int = 0
    preempted_total: int = 0
    failed_total: int = 0
    timeout_total: int = 0
    stuck_removed_total: int = 0
    emergency_ticks: int = 0
```

璇存槑锛?1. `blocked_total` 鏄樆鏂簨浠舵鏁帮紝涓嶆槸鍞竴浠诲姟鏁般€?2. `blocked_task_total` 鏄敮涓€琚樆鏂换鍔℃暟锛岀洿鎺ョ敱璋冨害鍣ㄧ淮鎶ゃ€?
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

璇存槑锛?1. `mode` 鍙栧€硷細`NORMAL/HIGH/EMERGENCY`銆?2. 鏄瘡杞皟搴︾殑鍙璁¤緭鍑哄崟鍏冦€?
## 7. Affinity Extension (R4)
1. `TaskSpec.target_gpu_index` is optional.
2. If set, scheduler projects GPU admission on the target card instead of global riskiest card.
3. `ResourceSnapshot.gpu_cards` stores per-card metrics from monitor sampling.
4. Invalid target index is rejected explicitly (`target gpu unavailable`).

## 8. Event Observability (R5)
1. `TASK_BLOCKED` event payload now includes `source`.
2. `source="admission"` means blocked during normal admission attempt.
3. `source="pending"` means blocked while queue is held in `EMERGENCY` mode.

## 9. Preemption Accounting (R8)
1. `stuck_removed_total` counts forced removals after stop timeout.
2. Forced removal now also updates reason-specific metrics:
`PREEMPTED` contributes to `preempted_total`, `TIMEOUT` contributes to `timeout_total`.
3. In emergency reclaim loop, a task removed from `running_set` is treated as effective reclaim even when `stop_task()` returns `false` (stuck-removal path).

## 10. Dry-Run Admission Cache (R9)
1. During one tick, running estimated load is computed once and updated incrementally as tasks start.
2. Cache fields include:
`running_est_mem_mb`, `running_est_cpu_pct`, `running_gpu_unbound_mb`, `running_gpu_by_index`.
3. This preserves dry-run projection correctness while reducing repeated full traversal of `running_set`.

## 11. Emergency Preemption View and Score (R11)
1. `preempt_low_priority` accepts both `snapshot` (smoothed) and optional `raw_snapshot`.
2. Emergency-dimension detection uses `raw_snapshot` first (`emergency_view`), consistent with mode decision path.
3. Mixed emergency ranking uses normalized synergy score:
`score = mem_unit + gpu_unit + min(mem_unit, gpu_unit)`.
4. If both reclaim targets are already zero, preemption loop exits immediately (no cooldown over-preemption).

## 12. Resource Profile Auto-Calibration (R15)
1. `TaskSpec.profile_key` identifies reusable profile buckets (default: command[0]).
2. Runtime sampling tracks per-task observed peak memory, normalized CPU, and process-level GPU memory (if available).
3. Completed/stopped tasks update a per-profile EMA:
`ema <- alpha * observed + (1-alpha) * previous`.
4. If `enable_estimation_autocalibration=true` and `samples >= profile_min_samples`, new submissions are conservatively upgraded by:
`calibrated = ema * profile_safety_multiplier` (for memory/CPU/GPU respectively).
5. Scheduler emits:
`TASK_PROFILE_UPDATED` and `TASK_ESTIMATE_CALIBRATED` for auditable adaptation behavior.

## 13. Real-Baseline Result Fields (R19/R20)
`run_advanced_research.py` 鐨勭湡鏈哄熀绾胯緭鍑轰腑锛宍C_dynamic_scheduler` 妯″紡鍖呭惈锛?1. `started_total`锛氭湰杞疄闄呭惎鍔ㄤ换鍔℃暟銆?2. `low_signal_dynamic`锛氫綆淇″彿鏍囪锛堜緥濡傞浂鍚姩鎴栨棤鍏抽敭璋冨害浜嬩欢锛夈€?3. `emergency_signal_missing`锛氱己澶辩揣鎬?鍥炴敹璇佹嵁鏍囪锛坄emergency_ticks==0 && preempted_total==0`锛夈€?4. `cpu_clip_events`锛氬疄楠屼笓鐢?CPU 鍘诲亸鐩戣鍣ㄨЕ鍙戞鏁般€?5. `peak_gpu_memory_pct`锛圓/B/C 鍚勬ā寮忥級搴旀弧瓒?`[0, 100]`锛岃秴鑼冨洿鍊艰涓洪噰鏍峰紓甯稿苟杩囨护銆?
褰撳惎鐢ㄧ洰鏍囦簨浠堕┍鍔ㄩ噸璇曪紙R20锛夋椂锛岃緭鍑洪澶栧寘鍚皾璇曡建杩癸細
1. `attempt`锛氬皾璇曞簭鍙枫€?2. `params`锛氳杞换鍔℃暟/鏃堕暱/鍐呭瓨鍙傛暟銆?3. `params.dynamic_memory_high_pct` / `params.dynamic_memory_emergency_pct` / `params.dynamic_preempt_count_per_tick`锛?璇ヨ疆鍔ㄦ€佽皟搴﹂槇鍊煎弬鏁帮紙R21锛夈€?4. `dynamic_summary`锛氳杞姩鎬佹ā寮忓叧閿寚鏍囨憳瑕併€?5. `retry_reason`锛氱户缁噸璇曠殑鍘熷洜锛圧22锛夛紝鍙栧€肩ず渚嬶細
`low_signal_dynamic`銆乣missing_emergency_signal`銆乣insufficient_completion`銆乣satisfied`銆?
褰撳惎鐢ㄥ弻鐩爣璇佹嵁妯″紡锛圧22锛夋椂锛岄澶栫害鏉燂細
1. `require_completion=true`锛?2. `min_completed` 鎸囧畾鍔ㄦ€侀樁娈垫渶灏忓畬鎴愪换鍔℃暟锛?3. 鍙湁鍚屾椂婊¤冻瀹夊叏鐩爣鍜屽悶鍚愮洰鏍囨墠鍋滄閲嶈瘯銆?
## R23 Attempt Adaptation Trace
When dual-objective eventful retry is enabled, each attempt trace additionally records:
1. 'threshold_bias': floating-point bias applied to dynamic threshold planning for this attempt.
2. 'dynamic_memory_high_pct' and 'dynamic_memory_emergency_pct': final thresholds after bias application.
3. 'retry_reason': reason code used to decide next-step adaptation.
4. 'max_scheduler_wall_sec': per-attempt scheduler wall budget after reason-aware adjustment.
5. 'adaptation_action': one of 'tighten_and_escalate', 'relax_and_hold', or 'stop'.