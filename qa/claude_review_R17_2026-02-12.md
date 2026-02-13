# Claude Deep Review — R17 (2026-02-12)

## 0. Review Scope

**Submitted for review**: R20 self-audit (`deep_algorithm_self_audit_R20_2026-02-12.md`)
**Actually reviewed**: R20 + undeclared R21 work interleaved in same commit.

| 维度 | R20（声明） | R21（未声明，实际交付） |
|------|-------------|-------------------------|
| 事件驱动重试 | `need_eventful_retry`, `escalate_real_baseline_params`, `run_real_machine_baseline_until_eventful` | — |
| 阈值渐进降低 | — | `plan_eventful_scheduler_thresholds`，修改 `run_real_machine_baseline` 签名，新增 `dynamic_*` 参数 |
| 尝试轨迹导出 | CSV `REAL-BASELINE-ATTEMPT` 行 | 含 `dynamic_memory_high_pct` / `dynamic_memory_emergency_pct` / `dynamic_preempt_count_per_tick` 字段 |
| GPU PID 解析测试 | `test_gpu_pid_memory_parser_aggregates_and_skips_invalid_rows` | — |
| 阈值降低测试 | — | `test_plan_eventful_scheduler_thresholds_are_valid_and_tighten` |
| `until_eventful` 测试增强 | — | 验证 `dynamic_memory_high_pct` kwargs 递减 |
| Spec 同步 | architecture.md, pseudocode.md, data_model.md (R20) | data_model.md §13 含 R21 字段 |

**Verdict**: **PASS**

---

## 1. Test Execution

```
> python -m pytest prototype/tests/ -v    → 70 passed, 0 failed
```

| 轮次 | 声明 | 实际 | 差异 |
|------|------|------|------|
| R19 self-audit | 65 | 69 | ISSUE-59 |
| R20 self-audit | 69 | 70 | ISSUE-59 持续 |

**注意**：首次运行遇到 `ImportError: cannot import name 'plan_eventful_scheduler_thresholds'`，
清除全部 `__pycache__` 和 `.pyc` 后通过。**这是连续第二轮出现陈旧字节码缓存问题**。

---

## 2. Math Verification

### 2.1 `plan_eventful_scheduler_thresholds(idx)` 阈值递降表

```python
memory_high_pct    = max(60.0, 76.0 - 5.0 * idx)
memory_emergency_pct = min(100.0, max(high + 4.0, 82.0 - 6.0 * idx))
guard: if high >= emergency: high = emergency - 1
preempt_count = max(1, 1 + idx // 2)
```

| idx | high_raw | high_clamped | emer_raw (82-6i) | emer_max(h+4, raw) | emer_clamped | preempt |
|-----|----------|--------------|------------------|--------------------|--------------|---------|
| 0   | 76.0     | 76.0         | 82.0             | max(80.0, 82.0)=82.0 | 82.0      | 1       |
| 1   | 71.0     | 71.0         | 76.0             | max(75.0, 76.0)=76.0 | 76.0      | 1       |
| 2   | 66.0     | 66.0         | 70.0             | max(70.0, 70.0)=70.0 | 70.0      | 2       |
| 3   | 61.0     | 61.0         | 64.0             | max(65.0, 64.0)=65.0 | 65.0      | 2       |
| 4   | 60.0     | 60.0         | 58.0             | max(64.0, 58.0)=64.0 | 64.0      | 3       |
| 5   | 60.0     | 60.0         | 52.0             | max(64.0, 52.0)=64.0 | 64.0      | 3       |
| 10  | 60.0     | 60.0         | -18.0            | max(64.0,-18.0)=64.0 | 64.0      | 6       |

**验证结果**:
- high 单调不递增 ✓
- emergency 单调不递增 ✓
- high < emergency 恒成立（gap ≥ 4pp）✓
- high ≥ 60.0 下限有效 ✓
- emergency ≤ 100.0 上限有效 ✓
- preempt_count 每两轮 +1 ✓
- idx ≥ 4 收敛到 (60.0, 64.0)，避免过度压缩 ✓

**设计洞察**：R21 阈值降低策略比 R20 单纯升压工作负载更巧妙 ——
降低调度器阈值使 EMERGENCY/PREEMPT 路径在低利用率下触发，避免 OOM 风险。
双管齐下（升压 + 降阈）使真机实验更有可能观测到完整调度事件链。

### 2.2 `escalate_real_baseline_params` 递增逻辑

```python
next_task_count = task_count + max(2, workers // 2)
next_duration_sec = min(20.0, max(6.0, duration) + 2.0)
next_base_mem_mb = max(256, round(base_mem * 1.25))
→ 再经 plan_real_baseline_params 安全约束
```

以测试用例为例 (task=8, dur=6.0, mem=1024, workers=4, host=16384):
- next_task=8+2=10, next_dur=min(20,8)=8.0, next_mem=max(256,1280)=1280
- plan_real_baseline_params(10, 8.0, 1280, 4, 16384):
  - base_mem_mb ≥ 1024 → keep 1280 ✓
  - safe_budget = 16384 * 0.9 = 14745.6
  - per_task = 1280 * 1.3 = 1664.0
  - max_safe = ⌊14745.6 / 1664.0⌋ = 8
  - task_count = min(10, 8) = 8（cap 触发）
  - 返回 task_count=8(≯8), duration=8.0(>6), base_mem=1280(>1024)
  - test assert: `(dur>6) or (mem>1024) or (task>8)` → dur=8.0>6.0 → True ✓

### 2.3 `run_real_machine_baseline` 阈值注入

```python
cfg = SchedulerConfig(
    memory_high_pct=float(dynamic_memory_high_pct),    # line 1033
    memory_emergency_pct=float(dynamic_memory_emergency_pct),  # line 1034
    cpu_high_pct=float(dynamic_cpu_high_pct),           # line 1035
    cpu_hard_pct=float(dynamic_cpu_hard_pct),            # line 1036
    preempt_count_per_tick=int(max(1, dynamic_preempt_count_per_tick)),  # line 1037
)
```

- 默认值 (85.0, 92.0, 99.9, 100.0, 1) 与非事件驱动模式行为一致 ✓
- `until_eventful` 调用时传入 `plan_eventful_scheduler_thresholds(idx)` 输出 ✓
- 第一轮 idx=0: high=76.0, emer=82.0 — 比默认 85/92 已显著降低 ✓

### 2.4 `until_eventful` 两路协同

```
attempt 0: plan thresholds(0) → high=76/emer=82, workload=initial
attempt 1: plan thresholds(1) → high=71/emer=76, workload=escalate(initial)
attempt 2: plan thresholds(2) → high=66/emer=70, workload=escalate(escalate(initial))
...
```

测试覆盖：
- mock 第一轮 low_signal=1 → retry → 第二轮 low_signal=0 → 停止 ✓
- 验证 second_call.high ≤ first_call.high ✓
- 验证 second_call.emer ≤ first_call.emer ✓
- 验证 call_count=2, eventful_achieved=1 ✓

---

## 3. Attempt Trace CSV 导出

`REAL-BASELINE-ATTEMPT` 行（lines 1445-1469）包含：
- 轮次标识: `evidence_id`, `attempt`, `seed`
- 工作负载参数: `task_count`, `task_duration_sec`, `base_mem_mb`, `fixed_workers`
- 阈值参数: `dynamic_memory_high_pct`, `dynamic_memory_emergency_pct`, `dynamic_preempt_count_per_tick`
- 调度事件指标: `started_total`, `blocked_event_total`, `preempted_total`, `emergency_ticks`
- 质量标记: `low_signal_dynamic`, `emergency_signal_missing`, `scheduler_timeout_hit`, `retry_needed`

**评估**: 字段完整，JSON → CSV 映射正确。每轮参数 + 结果可追溯。✓

---

## 4. CLI 集成

```
--real-target-eventful   (store_true)
--real-max-attempts      (int, default=3)
--real-attempt-seed-step (int, default=37)
```

流程优先级：`real_repeat_runs ≥ 2` > `real_target_eventful` > 单次运行。
`payload["real_baseline"]` 始终被填充（取 eventful 最后一轮 `final_result`），确保下游兼容。✓

---

## 5. Findings

### ISSUE-59 (Low) — 自审计测试计数错误（持续）
- R19 声明 65/65，实际 69/69
- R20 声明 69/69，实际 70/70
- 原因：R21 新增 `test_plan_eventful_scheduler_thresholds_are_valid_and_tighten`
- 建议：自审计应在 `python -m pytest --co -q` 后再写测试数

### ISSUE-60 (Info) — R21 工作未在 R20 审计中声明
- `plan_eventful_scheduler_thresholds` 函数 + 测试 + `run_real_machine_baseline` 签名修改均属 R21 范围
- R20 自审计仅提及 R20 内容
- 影响低（代码质量好，无遗漏风险），但审计完整性需注意

### ISSUE-61 (Low) — CPU 阈值硬编码 99.9/100.0
- `plan_eventful_scheduler_thresholds` 始终返回 `cpu_high=99.9, cpu_hard=100.0`
- 这实际上关闭了 CPU 模式检测（合理，因为真机基线专注内存）
- 但若未来场景需要 CPU 事件，此设计需修改
- 当前属"已知限制"而非缺陷

### OBS-10 (Info) — 陈旧字节码缓存连续两轮出现
- R16 和 R17 评审均因 `__pycache__` 导致 ImportError
- 建议：在 CI 或自审计验证步骤中加 `find . -name __pycache__ -exec rm -rf {} +` 前置清理

---

## 6. Issue Status Update

| ID | Severity | Status | 说明 |
|----|----------|--------|------|
| ISSUE-51 | Med | OPEN | CNIPA 检索仍未执行 |
| ISSUE-55 | Med | OPEN | RS-P01 逐权利要求对比未完成 |
| ISSUE-58 | Med | PARTIALLY FIXED | 参数规划 + 质量标记已到位；阈值降低策略 R21 补齐；但真机仍未观测到 emergency_ticks>0 |
| ISSUE-59 | Low | OPEN | 测试计数 70 vs 声明 69 |
| ISSUE-60 | Info | NEW | R21 未在 R20 审计中声明 |
| ISSUE-61 | Low | NEW | CPU 阈值硬编码 99.9/100.0 |
| OBS-10 | Info | NEW | 陈旧字节码缓存应在验证流程中前置清理 |

---

## 7. Verified Fixes (R20/R21)

| Fix | 验证方式 |
|-----|----------|
| F-30: `need_eventful_retry` 正确检测低信号 | 单元测试 + 代码逻辑审查 ✓ |
| F-31: `escalate_real_baseline_params` 至少一维递增 | 数学追溯 + 单元测试 ✓ |
| F-32: `plan_eventful_scheduler_thresholds` 单调递降且安全 | 完整数表追溯 idx=0..10 ✓ |
| F-33: `run_real_machine_baseline` 接受动态阈值参数 | 签名+SchedulerConfig注入审查 ✓ |
| F-34: `until_eventful` 双路协同 | Mock测试 + 代码流追溯 ✓ |
| F-35: 尝试轨迹 CSV 导出 | 字段映射审查 ✓ |
| F-36: GPU PID 解析回归测试 | 单元测试覆盖 ✓ |

---

## 8. Overall Assessment

**PASS** — R20 事件驱动重试 + R21 阈值降低策略质量高。

**优点**：
1. **设计巧妙**：阈值降低比工作负载升压更安全，避免 OOM 同时提高触发 EMERGENCY 的概率。
2. **双管齐下**：工作负载递增（escalate）+ 阈值递降（plan_thresholds）同步推进。
3. **完整审计链**：每轮尝试参数 + 调度事件指标 + 质量标记全部序列化到 CSV。
4. **测试覆盖**：阈值单调性 + 安全区间 + mock 集成 + kwargs 递减验证。

**关注点**：
1. 真机实验仍未触发 emergency+preempt 全链路（ISSUE-58 部分解决）。
2. 自审计测试计数持续偏差（ISSUE-59）。
3. R21 内容应在自审计中明确声明（ISSUE-60）。

---

## 9. Next Steps (R22 建议)

1. **执行真机事件驱动实验**：
   `--real-target-eventful --real-max-attempts 5` 验证阈值降低策略是否能在实际环境触发 emergency+preempt。
2. **自审计流程改进**：前置 `pytest --co -q | wc -l` + `rm -rf __pycache__`。
3. **ISSUE-58 收敛**：若 max_attempts=5 仍无事件，考虑在 CI 环境（无外部负载）重跑。
4. **ISSUE-51/55**：专利前置工作——CNIPA 检索 + RS-P01 权利要求级对比。
5. **专利文档更新**：claim 1 同步 synergy scoring 公式；说明书补阈值自适应机制描述。

---

*Reviewed by Claude Opus 4.6 — 2026-02-12*
