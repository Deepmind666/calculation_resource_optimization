# Claude Review R16 — 2026-02-12

**Scope**: Codex R19 (GPU 画像自校准闭环 + ISSUE-58 真机基线修复) + 未声明的 R20 (事件驱动真机基线重试)
**Reviewer**: Claude Opus 4.6
**Verdict**: **PASS** — R19 核心变更数学正确、测试充分; R20 代码质量好但需正式声明

---

## 1  测试与验证

| 检查项 | 结果 |
|--------|------|
| `python -m unittest discover` | **69/69 PASS** (首次因 `__pycache__` 过期报 ImportError, 清缓存后全通过) |
| `qa/validate_scheduler_config.py` | PASS |
| `prototype/run_experiments.py` | PASS (4 场景) |
| `prototype/run_patent_evidence.py` | PASS (P-02 + P-03) |
| Algorithm pseudocode 一致性 | `algorithm_pseudocode.md:310-382` 与代码完全匹配 ✓ |

**ISSUE-59 (Low): 自审测试数再次不一致**
R19 自审声称 65/65, 实际为 69/69。差异来源: R20 功能代码和 5 个额外测试在自审编写后追加。与 ISSUE-56 (58 vs 60) 为同一模式。

**OBS-05 (Info): 首次运行 `__pycache__` 过期导致 ImportError**
`test_advanced_research.py` 首次运行时因 `.pyc` 文件未反映最新 `run_advanced_research.py` 而报 `cannot import name 'escalate_real_baseline_params'`。清除 `__pycache__` 后恢复。非代码缺陷, 是并发编辑的工作流问题。

## 2  R19 核心变更: GPU 画像自校准

### 2.1  数据模型新增

| 组件 | 新增字段 | 类型 | 位置 |
|------|----------|------|------|
| `TaskSpec` | `target_gpu_index`, `profile_key` | `Optional[int]`, `Optional[str]` | line 41-42 |
| `TaskRuntime` | `observed_peak_gpu_mem_mb`, `last_sample_ts`, `ps_process` | `float`, `float`, `Optional[Any]` | line 98-100 |
| `ResourceProfile` | `ema_peak_gpu_mem_mb` | `float` | line 108 |
| `SchedulerConfig` | 6 个新配置项 | 详见下表 | line 78-83 |

| 新配置项 | 默认值 | 验证规则 | 代码行 |
|----------|--------|----------|--------|
| `enable_estimation_autocalibration` | `False` | — | 78 |
| `profile_ema_alpha` | `0.5` | ∈ [0, 1] | 79, 1120 |
| `profile_safety_multiplier` | `1.25` | ≥ 1.0 | 80, 1122 |
| `profile_min_samples` | `3` | ≥ 1 | 81, 1124 |
| `runtime_sample_interval_sec` | `0.2` | > 0 | 82, 1126 |
| `max_resource_profiles` | `1024` | ≥ 1 | 83, 1128 |

`enable_estimation_autocalibration=False` → 默认关闭, 不影响现有行为。✓

### 2.2  GPU 采样链路 (仅 non-dry-run 路径)

```
_refresh_running() → _sample_runtime_usage(runtime, now)
                   → psutil.Process(pid).memory_info().rss → observed_peak_mem_mb
                   → psutil.Process(pid).cpu_percent()     → observed_peak_cpu_pct
                   → _gpu_usage_mb_for_pid(pid, now)       → observed_peak_gpu_mem_mb
                       → _read_gpu_pid_memory_mb()  [带间隔缓存]
                           → nvidia-smi --query-compute-apps=pid,used_gpu_memory
```

**关键设计决策**:
1. GPU 进程采样使用 `nvidia-smi --query-compute-apps`, 与系统级 `--query-gpu` 分离 — 避免只看全局显存而不知进程级分布 ✓
2. PID 显存缓存共享 (`_gpu_pid_mem_cache`) — 同一 tick 内多任务只调一次 nvidia-smi ✓
3. 缓存间隔复用 `runtime_sample_interval_sec` — 可配置 ✓
4. `dry_run` 模式跳过采样 (line 949: `if self.config.dry_run... return`) — 正确, dry_run 无真实进程 ✓

### 2.3  EMA 更新逻辑数学验证

`_update_resource_profile` (lines 976-1022):

**初始化** (samples == 0):
- 直接设置 ema = observed (不混入零初始值) ✓

**后续更新**:
```
ema_new = α × observed + (1 - α) × ema_old
```

手算验证 (α=0.5, GPU):
| 步骤 | observed | ema_old | ema_new |
|------|----------|---------|---------|
| r1 (samples=0) | 1000 | — | 1000 |
| r2 (samples=1) | 1400 | 1000 | 0.5×1400 + 0.5×1000 = **1200** |

测试断言: `assertAlmostEqual(profile.ema_peak_gpu_mem_mb, 1200.0)` ✓ **完全匹配**

**边界条件**:
- `observed <= 0` → 跳过更新 (不污染画像) ✓
- 画像池满 → LRU 驱逐 (按 `last_updated_ts` 最小值) ✓
- 测试 `test_resource_profile_pool_is_bounded`: cap=2, 插入 A/B/C → A 被驱逐 ✓

### 2.4  估算校准逻辑数学验证

`_apply_estimation_profile` (lines 853-900):

```
gpu_candidate = int(max(0, ema_peak_gpu × safety_multiplier))
adjusted_gpu = max(task.estimated_gpu, gpu_candidate)
```

手算验证:
| 参数 | 值 |
|------|-----|
| profile.ema_peak_gpu_mem_mb | 900.0 |
| profile_safety_multiplier | 1.2 |
| task.estimated_gpu_mem_mb | 100 |
| gpu_candidate | int(900 × 1.2) = **1080** |
| adjusted_gpu | max(100, 1080) = **1080** |

测试断言: `assertGreaterEqual(queued.estimated_gpu_mem_mb, 1080)` ✓ **完全匹配**

### 2.5  nvidia-smi 输出解析验证

`_read_gpu_pid_memory_mb` (lines 902-937):

测试输入:
```
123, 100
123, 50 MiB
456, N/A
bad line
789, 20
```

| 行 | PID | 解析 | 结果 |
|----|-----|------|------|
| `123, 100` | 123 | float("100") = 100 | usage[123] = 100 |
| `123, 50 MiB` | 123 | split()[0] = "50" → float = 50 | usage[123] = 100 + 50 = **150** |
| `456, N/A` | 456 | split()[0] = "N/A" → float 异常 → skip | ✗ |
| `bad line` | — | parts < 2 → skip | ✗ |
| `789, 20` | 789 | float("20") = 20 | usage[789] = **20** |

测试断言: `usage[123]=150.0, usage[789]=20.0, 456 not in usage` ✓ **完全匹配**

注意: `parts[1].split()[0]` 巧妙处理了 nvidia-smi 可能输出 "123 MiB" 格式 — 只取数字部分。✓

## 3  R19 ISSUE-58 修复: 真机基线参数规划器

### 3.1  `plan_real_baseline_params` 数学验证

**测试 1**: task_count=18, duration=2.0, base_mem=96, workers=4, host=16384

| 步骤 | 计算 | 结果 |
|------|------|------|
| duration | max(2.0, 6.0) | **6.0** |
| min_task_count | max(4, 4+1) | 5 |
| task_count | max(18, 5) | 18 |
| base_floor (host≥16384) | 2048 | |
| base_mem | max(96, 2048) | **2048** |
| safe_budget | 16384 × 0.90 | 14745.6 |
| max_tasks | ⌊14745.6 / (2048×1.3)⌋ | 5 |
| task_count (capped) | | **5** |

断言: duration≥6.0 ✓, base_mem≥1024 ✓, 5≤task_count≤18 ✓, notes 非空 ✓

**测试 2**: task_count=20, duration=8.0, base_mem=2048, workers=4, host=16384
- max_tasks = 5, task_count 从 20 降至 5
- 断言: task_count < 20 ✓, ≥5 ✓, base_mem≥1024 ✓

**设计评估**:
1. 针对 R14 ISSUE-58 的根因 (base_mem_mb=96 太小): 直接拉升到 2048 ✓
2. 安全预算约束: 避免为触发 EMERGENCY 而制造 OOM 风险 ✓
3. duration 最低 6.0s 确保足够 tick 数 (≥60 ticks @ 0.1s interval) ✓

### 3.2  质量标记字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `started_total` | int | 动态模式启动任务数 — 若为 0 则调度器未被激活 |
| `low_signal_dynamic` | int | 综合低信号标记: blocked=0 且 preempted=0 且 emergency_ticks=0 |
| `emergency_signal_missing` | int | 未触发紧急/抢占事件 |
| `cpu_clip_events` | int | CpuCappedMonitor 裁剪次数 — 可追溯 CPU 噪声 |

这些标记解决了 R14 评审中"零启动假通过"的核心问题: 真机基线现在**不可能**在调度器完全未被激活的情况下被误认为"已覆盖证据路径"。✓

### 3.3  CpuCappedMonitor (实验专用)

`CpuCappedMonitor` (run_advanced_research.py line 768):
- 包装 `ResourceMonitor`, 将 CPU% > cap 裁剪到 cap (默认 99%)
- 仅用于实验路径, **不在核心调度器中**
- 目的: 防止宿主机 100% CPU 饱和导致全任务被阻断 (HIGH→EMERGENCY 误判)
- `clipped_samples` 计数器支持事后审计

评估: 合理的实验防御手段, 不污染核心算法。✓

## 4  R20 未声明变更: 事件驱动真机基线重试

R19 自审**未覆盖**以下三个新函数及其测试, 但代码和伪代码均已存在:

### 4.1  新增函数

| 函数 | 位置 | 功能 |
|------|------|------|
| `need_eventful_retry()` | line 1121 | 检查 `low_signal_dynamic` 或 `emergency_signal_missing` 标记 |
| `escalate_real_baseline_params()` | line 1127 | 提升 task_count (+2), duration (+2s), base_mem (×1.25), 然后通过 planner 安全收敛 |
| `run_real_machine_baseline_until_eventful()` | line 1152 | 循环执行真机基线, 直到触发目标事件或达到最大尝试次数 |

### 4.2  测试覆盖

| 测试 | 验证点 |
|------|--------|
| `test_need_eventful_retry_flags` | low_signal=1 → True, emergency_missing=1 → True, both=0 → False |
| `test_escalate_real_baseline_params_increases_pressure` | 至少一个维度增压 (duration/base_mem/task_count) |
| `test_run_real_machine_baseline_until_eventful_stops_early` | mock 首轮 low_signal, 二轮 eventful → 2 次调用后停止 |

### 4.3  评估

代码质量好, 测试设计合理。`escalate` 测试巧妙使用 `assertTrue(A or B or C)` 避免因 planner 安全降额导致 task_count 不一定增加的问题。

**但**: 未在自审中声明 = 评审盲区。建议后续正式提交 R20 自审文档。

### 4.4  伪代码同步

`algorithm_pseudocode.md:384-416` 包含 R20 伪代码, 与代码逻辑匹配 ✓

## 5  Issue 跟踪

| ID | 严重度 | 状态变更 | 详情 |
|----|--------|---------|------|
| ISSUE-58 | Med | **方向修复** | plan_real_baseline_params 自动提升弱参数; 质量标记防止假通过。仍未在强参数下获得 emergency_ticks>0 |
| ISSUE-59 | Low | NEW | 自审测试数 65 vs 实际 69, 同 ISSUE-56 模式 |
| ISSUE-56 | Low | OPEN | (延续) 自审测试计数机制需改进 |
| ISSUE-51 | Med | OPEN | CNIPA 搜索未执行 |
| ISSUE-55 | Med | OPEN | RS-P01 逐条权利要求未完成 |

### 新观察

**OBS-05 (Info): `__pycache__` 过期问题**
并发编辑导致 `.pyc` 文件与 `.py` 不同步。建议在自审验证步骤中加入 `find . -name __pycache__ -exec rm -rf {} +` 或在测试前自动清缓存。

**OBS-06 (Info): GPU 采样端到端路径无单元测试**
`_sample_runtime_usage` 的完整路径 (psutil + nvidia-smi → 峰值记录 → EMA 更新 → 估算校准) 在 dry_run=True 测试中被跳过。`_read_gpu_pid_memory_mb` 和 `_update_resource_profile` 单独测试了, 但集成路径依赖真实进程。可考虑 mock psutil.Process 做集成测试。

## 6  专利影响评估

### R19 对权利要求的影响

R19 的 GPU 画像自校准是**自校准特性**, 与核心三点发明 (CP-1/CP-2/CP-3) 正交。

| 与专利关系 | 评估 |
|-----------|------|
| CP-1 per-GPU 亲和 | 无直接影响 |
| CP-2 归一化抢占 | 无直接影响 |
| CP-3 双视图+累积 | 无直接影响 |
| **新可能从属权利要求** | "基于历史运行峰值的 EMA 画像自动校准任务资源估算" |

同意 R15 评审中的"先提交当前三点, 自校准作后续从属权利要求"策略。

### R19 对真机证据的影响

质量标记使真机基线从"无效数据"变为"可量化的低信号数据 + 自动提升建议"。ISSUE-58 方向性修复, 但仍需在更强参数下获得 `emergency_ticks > 0` 和 `preempted_total > 0` 才能构成专利证据。

## 7  Verdict

**PASS** — R19 是扎实的基础设施改进轮次。

**R19 亮点**:
1. GPU 画像自校准闭环完整: 采样 → EMA 更新 → 估算校准 → 准入影响
2. 所有新功能默认关闭 (`enable_estimation_autocalibration=False`), 不影响现有行为
3. 真机基线参数规划器解决了 ISSUE-58 根因, 质量标记防止假通过
4. Config 验证完整 (6 个新参数全部有验证规则)
5. nvidia-smi 输出解析健壮 (处理 MiB 后缀、N/A、畸形行)
6. 69/69 测试, 所有回归脚本通过

**R20 bonus**:
7. 事件驱动重试逻辑正确, 3 个测试, 伪代码同步
8. 需要正式 R20 自审文档

## 8  下一步

### P1: 修复当前问题
1. **ISSUE-59**: 自审测试数应反映实际 69 (建议自审流程增加 `python -m unittest discover 2>&1 | tail -1` 自动提取)
2. **R20 自审**: 为 `need_eventful_retry` + `escalate_real_baseline_params` + `run_real_machine_baseline_until_eventful` 补充正式自审

### P2: 真机证据获取
3. **强参数真机基线**: 用 `--run-real-baseline --real-base-mem-mb 3072 --real-fixed-workers 6 --real-task-duration-sec 10 --real-repeat-runs 3` 尝试触发 emergency+preempt
4. 或使用 R20 的 `run_real_machine_baseline_until_eventful` 自动搜索

### P3: 专利文件更新 (从 R15 延续)
5. **权利要求书 Claim 1 Step 6**: 增加"双维协同加分"
6. **说明书**: 增加 R17 协同评分公式和量化对比

### P4: 持续优先
7. **RS-P01 逐条权利要求** (ISSUE-55)
8. **CNIPA 搜索** (ISSUE-51)
