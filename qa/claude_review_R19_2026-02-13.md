# Claude Deep Review — R19 (2026-02-13)

## 0. Review Scope

**Submitted**: R23 self-audit (`deep_algorithm_self_audit_R23_2026-02-13.md`)
**Focus**: 自适应重试策略（按失败原因分支） + 真机双目标证据（安全 + 吞吐）

| 新增 | 文件 | 行号 |
|------|------|------|
| `apply_eventful_threshold_bias` | run_advanced_research.py | 903 |
| `update_eventful_threshold_bias` | run_advanced_research.py | 915 |
| `need_eventful_retry` 新增 `require_completion`/`min_completed` | run_advanced_research.py | 1175-1189 |
| `until_eventful` 自适应分支逻辑 | run_advanced_research.py | 1248-1322 |
| CLI args: `--real-require-completion`, `--real-min-completed` | run_advanced_research.py | CLI |
| test_apply_eventful_threshold_bias_is_reasonable | test_advanced_research.py | 250 |
| test_update_eventful_threshold_bias_rules | test_advanced_research.py | 263 |
| test_need_eventful_retry_can_require_completion | test_advanced_research.py | 205 |
| test_until_eventful_with_completion_requirement | test_advanced_research.py | 325 |

**Verdict**: **PASS**

---

## 1. Test Execution

```
> python -m unittest discover -s prototype/tests -p "test_*.py" -v
Ran 75 tests in 0.525s → OK
```

| 检查 | 状态 |
|------|------|
| 75/75 tests | PASS ✓ |
| 自审计声明 75/75 | 一致 ✓ |
| pycache 预清理后首次通过 | ✓ |
| run_experiments.py | PASS ✓ |
| run_patent_evidence.py | PASS ✓ |
| validate_scheduler_config.py | PASS ✓ |

---

## 2. Math Verification

### 2.1 `apply_eventful_threshold_bias(base_cfg, bias)`

```python
high = max(50.0, min(98.0, base.high + bias))
emergency = max(high + 1.0, min(99.0, base.emergency + bias))
```

| base (idx) | bias | high_raw | high_clamped | emer_raw | emer_clamped | gap |
|-----------|------|----------|-------------|----------|-------------|-----|
| idx=0 (76/82) | 0.0 | 76.0 | 76.0 | 82.0 | 82.0 | 6.0 |
| idx=0 (76/82) | +8.0 | 84.0 | 84.0 | 90.0 | 90.0 | 6.0 |
| idx=0 (76/82) | -6.0 | 70.0 | 70.0 | 76.0 | 76.0 | 6.0 |
| idx=1 (71/76) | -4.0 | 67.0 | 67.0 | 72.0 | 72.0 | 5.0 |
| idx=0 (76/82) | -30.0 | 46→50 | **50.0** | 52→**51.0** | 51.0 | 1.0 |
| idx=0 (76/82) | +25.0 | 101→98 | **98.0** | 107→**99.0** | 99.0 | 1.0 |

**验证结果**:
- 正向 bias 放宽阈值 ✓
- 负向 bias 收紧阈值 ✓
- high < emergency 恒成立（gap ≥ 1.0） ✓
- 边界 clamp [50, 98] / [high+1, 99] 有效 ✓

### 2.2 `update_eventful_threshold_bias(current, reason)`

```python
"insufficient_completion" → min(20.0, current + 8.0)   # RELAX
"low_signal_dynamic"      → max(-20.0, current - 4.0)  # TIGHTEN
"missing_emergency_signal" → max(-20.0, current - 4.0)  # TIGHTEN
"missing_dynamic_row"     → max(-20.0, current - 4.0)  # TIGHTEN
other                     → current                     # NO-OP
```

| current | reason | result | 验证 |
|---------|--------|--------|------|
| 0.0 | insufficient_completion | 8.0 | min(20, 0+8) = 8 ✓ |
| 19.0 | insufficient_completion | 20.0 | min(20, 19+8=27) = 20 ✓ |
| 0.0 | low_signal_dynamic | -4.0 | max(-20, 0-4) = -4 ✓ |
| -19.0 | missing_emergency_signal | -20.0 | max(-20, -19-4=-23) = -20 ✓ |
| 3.0 | missing_dynamic_row | -1.0 | max(-20, 3-4) = -1 ✓ |
| 1.5 | satisfied | 1.5 | no-op ✓ |

### 2.3 Adaptive Retry — 真机 Attempt 1 追溯

```
idx=0, threshold_bias=0.0
base = plan_thresholds(0) = {high:76, emer:82}
apply_bias(base, 0.0) → {high:76.0, emer:82.0}  ← matches JSON ✓

Result: emergency_ticks=0, emergency_signal_missing=1
→ need_eventful_retry: missing_emergency → True, "missing_emergency_signal"
→ adaptation_action = "tighten_and_escalate" ← matches JSON ✓

Escalate workload:
  escalate(6, 6.0, 2048, 4, host=64791):
    next_task = 6 + max(2, 4//2) = 8
    next_dur = min(20, 6+2) = 8.0
    next_mem = max(256, round(2048×1.25)) = 2560
    plan(8, 8.0, 2560, 4):
      safe_budget = 64791×0.9 = 58312
      per_task = 2560×1.3 = 3328
      max_safe = ⌊58312/3328⌋ = 17 > 8 → task_count=8 ✓

threshold_bias = update(0.0, "missing_emergency_signal") = -4.0 ✓
wall stays 12.0 (not insufficient_completion) ✓
```

### 2.4 Adaptive Retry — 真机 Attempt 2 追溯

```
idx=1, threshold_bias=-4.0
base = plan_thresholds(1) = {high:71, emer:76}
apply_bias(base, -4.0):
  high = max(50, min(98, 71-4)) = 67.0 ✓
  emer = max(67+1, min(99, 76-4)) = max(68, 72) = 72.0 ✓

Result: started=5, completed=3, emergency_ticks=13, preempted=2
→ need_eventful_retry(require_completion=True, min_completed=1):
  low_signal=0 ✓, emergency_missing=0 ✓, completed=3 ≥ 1 ✓
  → False, "satisfied" ✓
→ adaptation_action = "stop" ✓
→ eventful_achieved = 1 ✓
```

### 2.5 `need_eventful_retry` 优先级链

```
low_signal_dynamic → missing_emergency_signal → insufficient_completion → satisfied
```

设计合理：低信号（实验无效）优先于缺少事件优先于吞吐不足。
若实验本身无效（low_signal），吞吐数据不可信，应先解决信号问题。✓

---

## 3. Real Machine Evidence — 双目标达成

### 3.1 Attempt 对比

| 维度 | Attempt 1 | Attempt 2 |
|------|-----------|-----------|
| task_count | 6 | 8 |
| base_mem_mb | 2048 | 2560 |
| duration_sec | 6.0 | 8.0 |
| high/emer | 76.0/82.0 | **67.0/72.0** |
| threshold_bias | 0.0 | **-4.0** |
| wall_sec | 12.0 | 12.0 |
| started | 1 | **5** |
| completed | 0 | **3** |
| emergency_ticks | 0 | **13** |
| preempted | 0 | **2** |
| blocked | 2 | **47** |
| low_signal | 0 | 0 |
| emergency_missing | **1** | 0 |

### 3.2 Three-Mode Comparison (Attempt 2)

| 模式 | submitted | completed | nonzero_exit | peak_mem% | throughput |
|------|-----------|-----------|--------------|-----------|-----------|
| A_no_scheduler | 8 | 8 | 0 | **96.3** | 0.70 tps |
| B_fixed(4) | 8 | 8 | 0 | 78.4 | 0.43 tps |
| C_dynamic | 8 | **3** | **0** | — | 0.25 tps |

### 3.3 Evidence Strength Assessment

| 维度 | R21 (R18评审) | R23 (本轮) | 提升 |
|------|---------------|------------|------|
| completed | **0** | **3** | 从零吞吐到有效产出 |
| emergency_ticks | 9 | **13** | 更多 EMERGENCY 周期 |
| preempted_total | 1 | **2** | 更多抢占证据 |
| blocked_event_total | 162 | 47 | 合理（更宽松阈值下更少拦截） |
| nonzero_exit (C) | 0 | **0** | 持续安全 |
| quality markers | clean | **clean** | 两轮一致 |
| 双目标 | 安全 only | **安全 + 吞吐** | 关键突破 |

**专利证据意义**：
- **安全性**：A 模式 peak_mem 96.3%（OOM 边缘），C 模式 0 个异常退出 + 47 次准入拦截
- **吞吐量**：C 模式成功完成 3/8 任务（在 12s 时限和活跃 EMERGENCY 下）
- **自适应能力**：attempt 1→2 自动识别问题（missing_emergency_signal）并调整策略
- **完整事件链**：EMERGENCY 检测 → 抢占 → 准入拦截 → 任务完成，全部在同一轮观测到

---

## 4. Code Quality Assessment

### 4.1 `need_eventful_retry` API 变更
返回类型从 `bool` 变为 `Tuple[bool, str]` — 破坏性变更，但：
- 所有调用点已更新（until_eventful 中解包 `retry_needed, retry_reason`）✓
- 旧测试 `test_need_eventful_retry_flags` 已更新为解包两值 ✓
- 新测试 `test_need_eventful_retry_can_require_completion` 覆盖新参数 ✓

### 4.2 Completion Requirement Test
```python
# test line 325-382
# Mock: attempt 1 → completed=0, emergency_ticks=2 → "insufficient_completion"
# Mock: attempt 2 → completed=2, emergency_ticks=1 → "satisfied"
# Asserts:
#   - second_call.wall > first_call.wall ✓ (wall budget increased)
#   - second_call.high ≥ first_call.high ✓ (thresholds relaxed)
#   - second_call.task_count == first_call.task_count ✓ (workload NOT escalated)
#   - second_call.base_mem == first_call.base_mem ✓ (workload NOT escalated)
```
完整覆盖 `relax_and_hold` 分支语义。✓

### 4.3 Bias Clamping Safety
- `update_bias`: clamped to [-20.0, +20.0] ✓
- `apply_bias`: high clamped to [50.0, 98.0], emergency clamped to [high+1, 99.0] ✓
- 极端 bias（±30）不会导致 high ≥ emergency ✓（math verified in §2.1）

### 4.4 Audit Trail
每轮尝试记录：
- `threshold_bias`: 当前偏移值
- `adaptation_action`: `tighten_and_escalate` / `relax_and_hold` / `stop`
- `retry_reason`: 精确分类（5 种）
- `params`: 完整参数快照（含动态阈值 + wall budget）
- `dynamic_summary`: 完整调度事件指标

CSV 输出新增 `threshold_bias` 和 `adaptation_action` 列。✓

---

## 5. Spec Sync

| 文件 | 内容 | 状态 |
|------|------|------|
| algorithm_pseudocode.md | `apply_eventful_threshold_bias`, `update_eventful_threshold_bias` 伪代码 | ✓ |
| architecture.md | R23 双目标自适应收敛机制描述 | ✓ |
| data_model.md | `threshold_bias`, `adaptation_action`, `require_completion`, `min_completed` 字段 | ✓ |

---

## 6. Findings

### ISSUE-62 (Info) — data_model.md 中文编码疑似损坏
data_model.md 中部分中文字符显示为乱码（`鎸囧畾鍔ㄦ€侀樁娈垫渶灏忓畬鎴愪换鍔?`）。
可能是编辑器/Codex 写入时编码不一致。不影响功能，但降低文档可读性。

### OBS-11 (Info) — Attempt 2 scheduler_timeout_hit=1
两轮尝试均触发 timeout（wall=12s），说明任务负载需要更长时间完成。
若需更完整的吞吐证据（如 completed ≥ 6），可考虑增大 `--real-max-wall-sec`。

---

## 7. Issue Status Update

| ID | Severity | 状态 | 说明 |
|----|----------|------|------|
| ISSUE-51 | Med | OPEN | CNIPA 检索仍未执行 |
| ISSUE-55 | Med | OPEN | RS-P01 逐权利要求对比未完成 |
| ISSUE-58 | Med | **CLOSED+** | R21 证明机制，R23 补充吞吐证据（completed=3） |
| ISSUE-61 | Low | OPEN | CPU 阈值硬编码（合理限制）|
| ISSUE-62 | Info | NEW | data_model.md 编码疑似损坏 |
| OBS-11 | Info | NEW | 12s wall timeout 限制吞吐证据完整性 |

---

## 8. Verified Fixes

| Fix | 验证方式 |
|-----|----------|
| F-40: `apply_eventful_threshold_bias` 放宽/收紧逻辑 | 数学追溯 6 组输入 + 单元测试 ✓ |
| F-41: `update_eventful_threshold_bias` 分支规则 | 数学追溯 6 组 + 单元测试 ✓ |
| F-42: `need_eventful_retry` 新增 completion 检查 | 优先级链分析 + 单元测试 ✓ |
| F-43: `until_eventful` 自适应分支 (relax_and_hold / tighten_and_escalate) | 真机 JSON 数据追溯 + mock 测试 ✓ |
| F-44: 真机双目标证据 (completed=3, emergency=13) | JSON 数据验证 + attempt 参数追溯 ✓ |
| F-45: 审计字段导出 (threshold_bias, adaptation_action, retry_reason) | JSON + CSV 检查 ✓ |

---

## 9. Overall Assessment

**PASS** — R23 自适应重试策略设计精良，真机实验首次同时达成安全+吞吐双目标。

**核心突破**：
1. **从单向升压到原因分支自适应**：`insufficient_completion` 放宽阈值（不升压），`missing_emergency` 收紧阈值（升压）。
2. **真机 completed=3**：从 R21 的 completed=0 跃升到 completed=3，证明调度器在保障安全的同时维持有效吞吐。
3. **完整审计链**：每轮 `threshold_bias` + `adaptation_action` + `retry_reason` 全记录，可追溯、可复现。
4. **测试覆盖完整**：5 个新测试覆盖 bias 计算、规则分支、completion requirement、mock 集成。

**从 70 → 75 测试**（+5）：
- test_apply_eventful_threshold_bias_is_reasonable
- test_update_eventful_threshold_bias_rules
- test_need_eventful_retry_can_require_completion
- test_run_real_machine_baseline_until_eventful_with_completion_requirement
- test_sample_gpu_peak_percent_skips_absurd_rows

---

## 10. Next Steps (R24+ 建议)

### P1 — 专利文本更新（优先级最高）
1. **说明书**：补充"按失败原因自适应阈值调整"机制描述（R23 核心创新）
2. **权利要求**：考虑增加从属权利要求覆盖自适应重试策略
3. **附图**：真机三模式对比数据表 + 自适应 attempt 轨迹图

### P2 — 前置检索
1. CNIPA 检索（ISSUE-51）
2. RS-P01 权利要求级对比（ISSUE-55）

### P3 — 可选增强
1. 增大 wall timeout（30-60s）重跑，获取 completed ≥ 5 的更强证据
2. 多轮 CI 统计双目标达成率（参考 multi-seed CI 模式）
3. 修复 data_model.md 编码问题（ISSUE-62）

---

*Reviewed by Claude Opus 4.6 — 2026-02-13*
