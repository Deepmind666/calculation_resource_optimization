# Claude 评审 R10 — F-21/F-22 抢占改进 + F-23/F-24 准入缓存与集成测试

- 时间戳：2026-02-11 12:00 +08:00
- 审查人：Claude (Opus 4.6)
- 对象：Codex `deep_algorithm_self_audit_R8`（F-21 stuck reclaim + F-22 GPU preemption）+ `deep_algorithm_self_audit_R10`（F-23 dry-run cache + F-24 EMA integration test）
- 前置：R9 PASS（BUG-3 修复 + F-20 per-GPU budget 验证）

---

## 第一部分：验证总览

| 项目 | 结果 |
|---|---|
| 单元测试 | 44/44 通过 ✓ |
| 配置校验 | PASS ✓ |
| 实验脚本 (run_experiments.py) | 正常 ✓ |
| 专利证据脚本 (run_patent_evidence.py) | 正常 ✓ |
| Claim mapping 行号抽查 | 正确 ✓ |

---

## 第二部分：F-21 stuck 移除回收修复

### 问题回顾

`_stop_task()` 对 stuck 任务返回 `False`。旧抢占循环仅在 `_stop_task` 返回 `True` 时计入回收量，导致 stuck 任务被强制移除后仍不计入回收 → 循环继续 → 过度多杀。

### 修复验证

**`_stop_task` 指标更新** (`resource_scheduler.py:665-674`):

```python
if elapsed >= self.config.stuck_task_timeout_sec:
    self.running.pop(task_id, None)
    self.metrics.stuck_removed_total += 1
    effective_reason = runtime.stop_reason or reason
    if effective_reason == "PREEMPTED":
        self.metrics.preempted_total += 1
    elif effective_reason == "TIMEOUT":
        self.metrics.timeout_total += 1
```

- `effective_reason = runtime.stop_reason or reason`：使用首次请求停止时的原因（记录于 line 659），确保指标分类正确 ✓
- 无 double-count 风险：只有 stuck 路径走到这里，normal 路径走 line 687-690 ✓

**抢占循环** (`resource_scheduler.py:775-784`):

```python
stopped = self._stop_task(task_id, "PREEMPTED")
removed = task_id not in self.running
if stopped or removed:
    preempted.append(task_id)
    reclaimed_mb += ...
```

- `removed = task_id not in self.running`：检测 stuck 强制移除 ✓
- 未超时的 stuck 任务仍返回 `False` 且仍在 running → 不计入回收 ✓

### 数学验证：`test_stuck_removed_counts_toward_preempt_reclaim_target` (line 910)

- STUCK-A: mem=1000MB, stuck (stop_reason="PREEMPTED", elapsed > timeout)
- RUN-B: mem=500MB, normal
- `reclaim_needed = memory_used(7041.2) - target(8192×0.8 - 512 = 6041.6) = 999.6 MB`
- STUCK-A 被强制移除 → `reclaimed_mb = 1000 >= 999.6` → goal met → 停止
- **结果**：仅 STUCK-A 被抢占，RUN-B 保留 ✓
- **修复前**：`_stop_task` 返回 False → 不计入 → 继续 → RUN-B 也被抢占（过度多杀）

### 判定：F-21 正确 ✓

---

## 第三部分：F-22 GPU 感知抢占

### 核心变更

1. **紧急维度识别** (line 698-714)：区分 memory_emergency 和 gpu_emergency
2. **热点卡识别** (line 708-714)：`hottest_gpu_index = max(gpu_cards, key=memory_percent)`
3. **压力感知评分** (line 716-732)：`resource_reclaim_score()` 根据紧急维度加权
4. **有效 GPU 回收** (line 734-744)：`effective_gpu_reclaim()` 区分同卡/跨卡/unbound
5. **双目标回收** (line 765-784)：memory + GPU 双回收目标联合停止

### 评分逻辑分析

| 场景 | 内存评分 | GPU 评分 | 说明 |
|---|---|---|---|
| 仅 memory_emergency | `mem_mb` | 0 | 经典内存排序 |
| 仅 gpu_emergency | 0 | `gpu_mb × affinity_weight` | GPU 定向排序 |
| 两者皆紧急 | `mem_mb` | `gpu_mb × affinity_weight` | 混合评分 |

| GPU affinity | 评分权重 | 回收权重 | 说明 |
|---|---|---|---|
| 同卡 (target == hottest) | 1.0 | 1.0 | 直接缓解瓶颈 |
| Unbound (target == None) | 0.5 | 0.5 | 可能在任意卡 |
| 跨卡 (target != hottest) | 0.1 | 0.0 | 不缓解当前热点 |

**评分vs回收不对称性**：评分中跨卡=0.1（微弱偏好），回收中跨卡=0.0（不计入目标达成）。这是正确的设计——排序时略偏好跨卡 GPU 任务（比纯 memory 任务多一点 GPU 相关性），但计量回收时承认跨卡抢占不缓解当前瓶颈。✓

### 数学验证：`test_gpu_emergency_preempts_gpu_heavy_task_first` (line 974)

- GPU-HEAVY: mem=200, gpu_mem=1200, target=card-0
- MEM-HEAVY: mem=5000, gpu_mem=0, target=card-0 (无 GPU 实际用量)
- GPU emergency: card-0 at 96%, hottest=card-0
- Memory: 60% (非紧急)

**评分**：
- GPU-HEAVY: `memory_emergency(F) or not gpu_emergency(F)` = F → skip mem. `gpu_emergency(T)`, gpu_mb=1200, target=0=hottest → 1200. **Total: 1200**
- MEM-HEAVY: skip mem. gpu_mb=0 → skip GPU. **Total: 0**

**排序**：GPU-HEAVY (1200) > MEM-HEAVY (0) → GPU-HEAVY 先被抢占

**回收检查**：
- `reclaim_needed_mb = max(0, mem_used - target)` ≈ 0（memory 不紧急）→ memory_goal_done = True
- `reclaim_needed_gpu_mb = 9600 - (10000×0.85) = 9600 - 8500 = 1100`
- `effective_gpu_reclaim(GPU-HEAVY) = 1200`（target=0=hottest → 1.0）
- `1200 >= 1100` → gpu_goal_done = True → 停止

**结果**：仅 GPU-HEAVY 被抢占 ✓

### 判定：F-22 正确 ✓

---

## 第四部分：F-23 dry-run 准入缓存（OBS-5 修复）

### 变更概要

- `tick()` line 264-270：在 tick 开始时一次性计算 running 估算
- `tick()` line 301-312：传递缓存值给 `_can_admit()`
- `tick()` line 319-334：准入成功后增量更新缓存
- `_can_admit()` line 505-524：新增 `running_est_*` 参数（Optional，兼容直接调用）

### 正确性验证

**等价性**：缓存值 + 增量更新 ≡ 每次重新调用 `_running_estimated_*`

追踪：
1. tick 开始：`running_est_mem_mb = sum(running.values().estimated_mem_mb)` — 所有已运行任务
2. 任务 A 准入 → `_start_task(A)` → A 加入 `self.running`
3. `running_est_mem_mb += A.estimated_mem_mb` — 手动增量
4. 若重新调用 `_running_estimated_load()` → 遍历 running（包含 A）→ 得到相同值 ✓

GPU 分解同理：bound 和 unbound 分别增量更新。✓

**后向兼容**：`running_est_mem_mb: Optional[float] = None` → 不传时 fallback 到内部计算 ✓

### 测试验证：`test_dry_run_running_estimate_computed_once_per_tick` (line 839)

- `patch.object` + `wraps` 计数调用次数
- 3 个任务提交，1 个 tick
- `load_mock.call_count == 1`，`gpu_mock.call_count == 1` ✓

### 性能改善

| 指标 | 修改前 | 修改后 |
|---|---|---|
| `_running_estimated_load` 调用/tick | O(P) 次（P=pending） | 1 次 |
| `_running_estimated_gpu_breakdown` 调用/tick | O(P) 次 | 1 次 |
| 每次调用复杂度 | O(R)（R=running） | O(1) 增量 |
| 总复杂度/tick | O(P×R) | O(R + P) |

### 判定：F-23 正确 ✓

---

## 第五部分：F-24 EMA 全路径集成测试

### 测试：`test_ema_alpha_full_tick_path_gpu_affinity_then_emergency_preempt` (line 219)

**覆盖路径**：
1. `ema_alpha=0.6` → 触发 `_smooth_snapshot` 构造路径（BUG-3 回归覆盖）
2. GPU affinity admission（target_gpu_index=0）→ 验证 gpu_cards 保留
3. Raw GPU spike (96% on card-0) → EMERGENCY 触发（双视图 P-02 覆盖）
4. GPU 感知抢占 → 验证 F-22 抢占逻辑

**断言**：
- Tick 2: `started == ["EMA-FULL-GPU-1"]` — affinity 准入成功 ✓
- Tick 3: `mode == "EMERGENCY"` — raw 触发 ✓
- Tick 3: `"EMA-FULL-GPU-1" in preempted` — GPU 任务被抢占 ✓

**这是 R9 建议的 P1 全路径测试，完全落实。** ✓

### 判定：F-24 正确 ✓

---

## 第六部分：NoCumulativeProjectionScheduler 签名同步

`run_patent_evidence.py:132-158` 更新：

```python
def _can_admit(self, ...,
    running_est_mem_mb: float | None = None,
    running_est_cpu_pct: float | None = None,
    running_gpu_unbound_mb: float | None = None,
    running_gpu_by_index: dict[int, float] | None = None,
) -> tuple[bool, str]:
    return super()._can_admit(
        ...,
        planned_extra_mem_mb=0.0,      # 归零累计投影
        planned_extra_cpu_pct=0.0,
        planned_extra_gpu_by_index={},
        planned_extra_gpu_unbound_mb=0.0,
        running_est_mem_mb=running_est_mem_mb,     # 保留 running 估算
        running_est_cpu_pct=running_est_cpu_pct,
        running_gpu_unbound_mb=running_gpu_unbound_mb,
        running_gpu_by_index=running_gpu_by_index,
    )
```

正确：归零 planned_extra（消融目的），保留 running_est（dry-run 正确性）。✓

---

## 第七部分：发现的问题

### ISSUE-36 [Low] — `_preempt_low_priority` 使用 smoothed snapshot 判断紧急维度

**位置**：`resource_scheduler.py:694-707`

**描述**：`_preempt_low_priority(snapshot)` 接收的是 EMA 平滑后的 snapshot。`memory_emergency` 和 `gpu_emergency` 基于 smoothed 值判断。但 EMERGENCY 模式本身是由 `_evaluate_mode` 使用 raw 值触发的。

**影响场景**：raw GPU spike 97% 但 EMA 平滑后 85% → `_evaluate_mode` 触发 EMERGENCY（看 raw）→ `_preempt_low_priority` 中 `gpu_emergency = (85 >= 95)` = False → GPU 感知排序不生效 → 退化为纯内存排序。

**严重程度**：Low — 系统仍在 EMERGENCY 模式，抢占仍然发生，只是排序不够精准。多 tick 后 EMA 会追上。且 memory_emergency 为 False 时 `memory_emergency or not gpu_emergency` = True → 仍用内存排序，不会完全失灵。

**建议修复**：将 `raw_snapshot` 也传入 `_preempt_low_priority`，用 raw 判断紧急维度。

### ISSUE-37 [Low] — 混合紧急场景下评分单位混淆

**位置**：`resource_scheduler.py:716-732`

**描述**：当 `memory_emergency=True AND gpu_emergency=True` 时，`resource_reclaim_score` 混合了内存 MB 和 GPU MB：`score = mem_mb + gpu_mb × weight`。不同任务的 mem/gpu 比例可能导致排序不符合主瓶颈预期。

例：任务 A (mem=5000, gpu=100 on hot card) → score=5100；任务 B (mem=200, gpu=5000 on hot card) → score=5200。若主瓶颈是内存，优先抢占 B 但只回收 200MB 内存，不如抢占 A 回收 5000MB。

**严重程度**：Low — 回收循环会继续直到 BOTH 目标满足，所以最终都会被抢占。影响仅是抢占顺序的效率。

### OBS-7 [Info] — Fix 编号与审计轮次编号体系不一致

Codex 自查使用独立的 R-编号（R8=stuck+GPU, R10=cache+EMA test），与 Claude 评审 R-编号（R8=BUG-3 深度审查, R9=BUG-3 fix, R10=本轮）不一致。同时 `data_model.md` Section 9 标注 "(R8)"、Section 10 标注 "(R9)" 与 Claude 编号混淆。

建议统一为单一编号体系，或在文档中明确区分"Codex Self-Audit Round" vs "Claude Review Round"。

---

## 第八部分：代码质量趋势

### 测试数量进展

```
R1:3 → R3:3 → R4:12 → R5:14 → R6:28 → R7:32 → R8:38 → R9:40 → R10:44
```

### Fix 进展总览

| Fix | 内容 | 严重度 | 来源 |
|---|---|---|---|
| F-01~F-06 | 紧急漏检/输入校验/重复ID/配置键/终止保护/日志上限 | Critical~Medium | Codex 自查 |
| F-07~F-08 | dry_run 双计数/多GPU | Critical/High | Claude R4 发现 |
| F-09~F-13 | SUG-8/9 + 测试缺口 | Medium~Low | Claude R4/R5 建议 |
| F-14~F-16 | GPU 采样/GPU 阈值/blocked 指标 | Medium~Low | Codex 自查 |
| F-17 | GPU affinity | Medium | Codex 新特性 |
| F-19 | BUG-3 修复（gpu_cards EMA 丢失）| Critical | Claude R8 发现 |
| F-20 | per-GPU planned budget | Medium | Codex 改进 |
| F-21 | stuck 回收计量修复 | Medium | Codex 自查 |
| F-22 | GPU 感知抢占 | Medium | Codex 新特性 |
| F-23 | dry-run 准入缓存 | Low (OBS-5) | Claude R9 建议 |
| F-24 | EMA 全路径集成测试 | Test | Claude R9 建议 |

### 评分维度

| 维度 | R9 | R10 | 变化 |
|---|---|---|---|
| 正确性 | 9/10 | 9/10 | 维持 |
| 测试质量 | 9/10 | **10/10** | +4 新测试，含全路径集成 |
| 文档配套 | 8/10 | 8/10 | 伪代码/数据模型同步 |
| 自检可信度 | 10/10 | **10/10** | F-21~F-24 全部真实修复 |
| 架构设计 | 8/10 | **9/10** | GPU 感知抢占是显著架构改进 |

---

## 第九部分：改进建议

### P1 — 建议优先执行

1. **ISSUE-36 修复**：将 `raw_snapshot` 传入 `_preempt_low_priority`，用 raw 判断紧急维度
   - 改为 `def _preempt_low_priority(self, snapshot, raw_snapshot=None):`
   - `emergency_view = raw_snapshot or snapshot`
   - 用 `emergency_view` 判断 `memory_emergency` 和 `gpu_emergency`
   - 这与 `_evaluate_mode` 的双视图策略一致

2. **做资源调度领域 prior art 正式检索**（R9 遗留 P1，仍未完成）

3. **重写 patent/ 目录**（R9 遗留 P1，仍未完成）

### P2 — 建议后续考虑

4. **ISSUE-37 优化**：混合紧急时可按归一化比例评分（`score = mem_mb/mem_typical + gpu_mb/gpu_typical`），避免单位混淆

5. **编号体系统一**（OBS-7）：建议 data_model.md 中使用 "Codex-R8" / "Claude-R9" 前缀

6. **F-22 可作为专利差异化特征**：GPU affinity 感知的紧急抢占（根据热点卡定向排序 + 双目标回收）在现有调度器中较少见。建议加入权利要求组合方案。

---

## 第十部分：前次评审遗留问题状态

| 编号 | 状态 | 说明 |
|---|---|---|
| BUG-1 | ✅ | F-07 已修 |
| BUG-2 | ✅ | F-09~F-13 已修 |
| BUG-3 | ✅ | F-19 已修 |
| ISSUE-9 | ⚠️ 未解决 | 项目方向分裂，需用户决策 |
| ISSUE-13 | ⚠️ 未解决 | prior_art 16 项"已核验"无证据 |
| OBS-5 | ✅ | F-23 已解决 |

---

## 判定

**PASS** ✓

- F-21 stuck 回收修复正确，防止过度多杀
- F-22 GPU 感知抢占逻辑合理，压力感知评分 + 双目标回收 + affinity 权重设计正确
- F-23 dry-run 缓存消除重复扫描，复杂度从 O(P×R) 降至 O(R+P)
- F-24 EMA 全路径集成测试覆盖 BUG-3 + P-02 + F-22 完整链路
- 2 个 Low 级新发现（ISSUE-36 smoothed vs raw, ISSUE-37 混合评分），无 Critical/High
- 44/44 测试全部通过
- 代码持续保持**生产就绪**状态

---

## 关于前一份工作报告的说明

Codex 前一份工作报告（提及 commit `aa478f5`、`cluster.py`、`models.py`、`merge_candidate_filter`、51/51 测试）中的所有文件和 commit 均不存在于本仓库。该报告疑似来自其他项目或上下文，与 `calculation_resource_optimization` 仓库无关。本轮评审仅涵盖当前工作树中实际存在的代码变更。

---

*审查人：Claude (Opus 4.6) — 所有断言均经逐行追踪 + 数学验证*
