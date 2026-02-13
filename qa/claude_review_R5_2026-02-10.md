# Claude 评审报告 R5 — 2026-02-10 13:00:00 +08:00

- 评审人：Claude (Opus 4.6)
- 评审范围：Codex commit `5594b53`（"fix: resolve R4 scheduler issues and sync review artifacts"）全部变更，含对 R4 所列 BUG-2、ISSUE-21/22/27 的修复响应
- 前置基线：Claude R4 评审（Conditional PASS，2026-02-10 11:30）
- 评审目标：逐条验证 R4 修复闭环、核查新增代码与文档、更新累计评分

---

## 〇、可执行性验证

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 单元测试 | **PASS** | 14/14 通过（0.072s），含 2 个新增测试 |
| 配置校验 | **PASS** | `qa/validate_scheduler_config.py` → PASS |
| 结构检查 | **PASS** | `qa/structure_check.ps1` → PASS |
| Git 提交 | **PASS** | `5594b53` 已推送 origin/main，10 文件变更，+842/-210 行 |

---

## 一、R4 必修项修复验证

### F-07 [Critical] BUG-2 — dry_run 模式同 tick 已启动任务双重计数

**Codex 声明**：已修复。dry_run 路径仅使用 `_running_estimated_load()`；real-run 路径仅使用 `planned_extra_*`。

**Claude 验证结果：确认已修复 ✓**

**代码审查**（`resource_scheduler.py:425-439`）：

```python
running_mem_est, running_cpu_est, running_gpu_est = self._running_estimated_load()
base_mem_mb = s.memory_used_mb
base_cpu_pct = s.cpu_percent
base_gpu_mb = 0.0
if self.config.dry_run:
    # dry_run running set already contains tasks started earlier in this tick.
    # Adding planned_extra_* again would double count.
    base_mem_mb += running_mem_est
    base_cpu_pct += running_cpu_est
    base_gpu_mb += running_gpu_est
else:
    # In real mode, planned_extra_* represents same-tick launches not reflected in snapshot yet.
    base_mem_mb += planned_extra_mem_mb
    base_cpu_pct += planned_extra_cpu_pct
    base_gpu_mb += planned_extra_gpu_mb
```

**逻辑正确性数学验证**：

1. **dry_run 模式**：`_start_task()` 立即将任务加入 `self.running`。因此 `_running_estimated_load()` 已包含同 tick 已启动任务。仅使用 `running_est`，不叠加 `planned_extra_*`，消除双重计数。

2. **real 模式**：`_start_task()` 虽然也将任务加入 `self.running`，但 `s`（资源快照）是 tick 开始时采样的，不反映同 tick 新启动的进程。因此 `planned_extra_*` 填补了快照与实际启动之间的时间差。仅使用 `planned_extra_*`，不叠加 `running_est`，亦无双重计数。

3. **跨 tick 任务处理**：
   - dry_run：前序 tick 任务仍在 `self.running` 中 → `running_est` 包含其估值 ✓
   - real：前序 tick 任务的内存已反映在 `s.memory_used_mb`（psutil 采样）中 → `planned_extra_*` 仅需追踪同 tick 新增 ✓

**测试验证**（`test_resource_scheduler.py:240-255`）：

```python
def test_dry_run_admission_no_double_count_same_tick(self):
    # snap(60, 20) → memory_used_mb = 4915.2, total = 8192
    # D1: 800MB, D2: 800MB
    # 修复后：D2 的 base_mem = 4915.2 + 800 = 5715.2
    #   projected = 5715.2 + 800 + 512 = 7027.2 → 85.78% < 92% → 通过
    # 修复前（双重计数）：base_mem = 4915.2 + 800 + 800 = 6515.2
    #   projected = 6515.2 + 800 + 512 = 7827.2 → 95.5% > 92% → 错误阻断
    self.assertEqual(len(report.started), 2)  # 两个都应启动
    self.assertEqual(len(report.blocked), 0)
```

**已有测试兼容性验证**：`test_batch_projection_prevents_oversubscribe_same_tick`（lines 95-111）在修复后仍然正确通过。该测试中 snap(70, 20) + 2×1000MB 任务，修复后第二个任务的 projected_mem_pct = 100.66% > 92% 仍被正确阻断。证明累计投影机制本身完好，之前的通过不依赖双重计数。

**注意事项**：`tick()` 中 `planned_extra_*` 仍在 dry_run 模式下被累加（lines 263-265），但在 `_can_admit` 中被忽略。这是无害的冗余，但略显不洁。此外 `_running_estimated_load()` 在 non-dry_run 分支中被调用但未使用（line 425），为 O(R) 轻量计算，可接受。

---

### F-08 [Medium] ISSUE-27 — 多 GPU 系统仅监控首张 GPU

**Codex 声明**：已修复。`_sample_gpu` 解析全部 GPU 行，按显存占比最高卡判定风险。

**Claude 验证结果：确认已修复 ✓**

**代码审查**（`resource_scheduler.py:148-184`）：

```python
rows: List[Tuple[float, float, float, float]] = []
for line in out.strip().splitlines():
    line = line.strip()
    if not line:
        continue
    parts = [x.strip() for x in line.split(",")]
    if len(parts) < 3:
        continue
    util = float(parts[0])
    used_mb = float(parts[1])
    total_mb = max(1.0, float(parts[2]))
    mem_pct = 100.0 * used_mb / total_mb
    rows.append((mem_pct, util, used_mb, total_mb))
if not rows:
    return {}
# With multiple GPUs, guard based on the riskiest (highest memory pct) card.
mem_pct, util, used_mb, total_mb = max(rows, key=lambda x: x[0])
```

**正确性分析**：
- 遍历 nvidia-smi 输出的所有行，而非仅取第一行 ✓
- 空行和格式错误行被安全跳过 ✓
- `total_mb` 使用 `max(1.0, ...)` 防除零 ✓
- `max(rows, key=lambda x: x[0])` 按 `mem_pct` 取最高风险卡 ✓
- 返回最高风险卡的 `util/mem_pct/used_mb/total_mb` 四维数据 ✓

**测试验证**（`test_resource_scheduler.py:257-269`）：

三张 GPU 测试数据：
| GPU | util% | used_mb | total_mb | **mem_pct** |
|:---:|:-----:|:-------:|:--------:|:-----------:|
| 0 | 20 | 1000 | 10000 | 10.0% |
| 1 | 30 | 7000 | 8000 | **87.5%** |
| 2 | 10 | 100 | 12000 | 0.83% |

测试断言 GPU 1（最高 87.5%）被选中，util=30, used=7000, total=8000。全部 4 个 `assertAlmostEqual` 验证精度到 3 位小数。

**设计合理性**：以"最坏卡"策略做防护判定是保守且安全的选择。R-05（任务级 GPU affinity）仍为后续优化方向，当前不影响安全性。

---

## 二、R4 建议项修复验证

### ISSUE-21 — 伪代码末尾残留孤立代码

**Codex 声明**：已修复，伪代码重写。

**Claude 验证结果：确认已修复 ✓**

`algorithm_pseudocode.md` 重写为 9 个 Section，全部在代码块内，无孤立行。文件末尾为 Section 9 "指标输出"后正常结束。

---

### ISSUE-22 — 伪代码与实现严重脱节

**Codex 声明**：已修复，伪代码与实现逐段对齐。

**Claude 验证结果：大部分已修复，发现 1 处残余脱节**

逐 Section 对比：

| Section | 伪代码内容 | 实现对应 | 对齐状态 |
|:-------:|-----------|----------|:--------:|
| 1 主循环 | raw+smooth+evaluate_mode+preempt+admit | `tick()` | ✓ 对齐 |
| 2 模式判定 | raw→emergency, smooth→high/normal, cooldown, hysteresis | `_evaluate_mode()` | **⚠ 见下** |
| 3 目标并发 | NORMAL/HIGH/EMERGENCY 分档 | `_compute_target_workers()` | ✓ 对齐 |
| 4 接纳控制 | dry_run vs real-run 双路径 | `_can_admit()` | ✓ 对齐 |
| 5 队列接纳 | 累计投影+blocked回推 | `tick()` 内循环 | ✓ 对齐 |
| 6 紧急回收 | preemptible+sort+reclaim_target | `_preempt_low_priority()` | ✓ 对齐 |
| 7 停止任务 | terminate→kill→poll 三级 | `_stop_task()` | ✓ 对齐 |
| 8 GPU 监控 | 多卡+max(mem_pct) | `_sample_gpu()` | ✓ 对齐 |
| 9 指标 | 8 个字段 | `SchedulerMetrics` | ✓ 对齐 |

**ISSUE-22-residual [Low] — Section 2 缺少 GPU 迟滞退出条件**

伪代码 lines 81-84：
```text
if previous_mode == HIGH and
   (smooth.memory_percent > cfg.memory_high_pct - cfg.mode_hysteresis_pct or
    smooth.cpu_percent > cfg.cpu_high_pct - cfg.mode_hysteresis_pct):
  return HIGH
```

实现 `resource_scheduler.py:394-402`：
```python
if self._mode == "HIGH":
    stay_high = s.memory_percent > mem_high_exit or s.cpu_percent > cpu_high_exit
    if (
        self.config.enable_gpu_guard
        and s.gpu_memory_percent is not None
        and s.gpu_memory_percent > gpu_high_exit   # ← 伪代码缺失此条件
    ):
        stay_high = True
    return "HIGH" if stay_high else "NORMAL"
```

伪代码遗漏了 GPU 迟滞退出检查。当 GPU 显存处于 `gpu_memory_high_pct - mode_hysteresis_pct` 到 `gpu_memory_high_pct` 之间时，实现会保持 HIGH 模式，但伪代码未描述此行为。

**严重程度：Low**。仅影响文档精度，不影响运行正确性。

---

### ISSUE-28 — `.claude.md` 编码损坏

**Codex 声明**：本轮未修改 `.claude.md`，避免二次破坏。

**Claude 评价**：**策略合理 ✓**。Codex 正确识别了编码破坏的根因（其工具链在 Windows 下可能使用了错误编码），并采用"回避策略"而非冒险修复。`.claude.md` 已由 Claude 在 R4 评审期间从 git HEAD 恢复。

---

### R1 ISSUE-2 / R3 ISSUE-12 — `igures/` 拼写错误

**Codex 声明**：已在 `logs/work_progress.md` 中清理。

**Claude 验证结果：确认已修复 ✓**

Grep 搜索 `logs/work_progress.md` 中的 `igures/`：**0 匹配**。经过 6 轮评审，该拼写错误终于被清理。

---

## 三、R4 建议项未处理状态

| R4 建议项 | 本轮状态 | Claude 评价 |
|----------|:--------:|------------|
| SUG-8（抢占排序方向：旧任务优先→新任务优先）| **未处理** | `_preempt_low_priority:560` 仍用 `-start_ts`（旧任务优先回收）。作为建议项，不阻塞。但建议后续考虑"沉没成本最小化"策略。 |
| SUG-9（不可终止任务超时逃逸）| **未处理** | `_stop_task` 返回 False 后任务永驻 running。作为建议项，不阻塞。建议后续增加 `max_stop_retries` 或 `stuck_task_timeout`。 |

---

## 四、数据模型文档验证

**文件**：`spec/data_model.md`（132 行，重写）

**Claude 验证结果：与实现一致 ✓**

逐 dataclass 对比：

| 数据类 | 字段数 | 与代码一致 | 约束描述 |
|--------|:------:|:----------:|:--------:|
| ResourceSnapshot | 11 | ✓ | — |
| TaskSpec | 9 | ✓ | task_id 唯一非空、priority ≥1、估值 ≥0 |
| SchedulerConfig | 22 | ✓ | worker 范围、阈值层级、超时正值 |
| TaskRuntime | 5 | ✓ | dry_run 用 remaining_ticks |
| SchedulerMetrics | 8 | ✓ | blocked_total 注明为事件次数 |
| TickReport | 8 | ✓ | mode 三态 |

特别肯定：`blocked_total` 注明为"阻断事件次数，不是唯一任务数"（line 112），消除了 R3-supplement ISSUE-19 的歧义。

---

## 五、Codex 自查报告复核

**文件**：`qa/self_audit_round1_2026-02-10.md`（120 行，更新）

Codex 现声称 F-01 ~ F-08 共 8 项修复，剩余 R-04/R-05 为低优先级。

| Codex 声明 | Claude 验证 |
|:----------:|:-----------:|
| F-01 ~ F-06：R4 已全部确认 | ✓ 维持确认 |
| F-07 [Critical]：干净修复 | ✓ 本轮确认（见一、F-07） |
| F-08 [Medium]：干净修复 | ✓ 本轮确认（见一、F-08） |
| R-04 [Low]：blocked 指标口径 | ✓ 不阻塞，已在实验脚本中补充 unique_blocked_tasks |
| R-05 [Low]：无任务级 GPU affinity | ✓ 不阻塞，属后续优化 |
| 14/14 测试通过 | ✓ Claude 独立验证通过 |
| 配置校验 PASS | ✓ Claude 独立验证通过 |
| 结构检查 PASS | ✓ Claude 独立验证通过 |

**Codex 自查可信度评价：继续保持高水平。** 本轮 2 个新增修复（F-07/F-08）全部真实有效，每个都有针对性测试。自查报告结构清晰，行号引用可核对。从 R3 的 2/10 到 R4 的 8/10，本轮维持 9/10（扣分点：F-04 行号引用与当前代码偏移，但不影响结论）。

---

## 六、R4 对比闭环报告复核

**文件**：`qa/r4_review_comparison_2026-02-10.md`（38 行，新增）

**Claude 评价：结构合理，内容诚实 ✓**

Codex 按 R4 的逐条发现制作了对比表，标注"已修复"/"未在本轮处理"，未虚报。对 ISSUE-28 的处置策略（避免覆盖写入）和 ISSUE-9（治理决策，需用户确认）的定位准确。

唯一微瑕：对 ISSUE-2 的描述"本轮已在日志中清理错误路径写法"，Grep 验证确认属实。

---

## 七、新发现问题

### ISSUE-29 [Low] — 伪代码 Section 2 遗漏 GPU 迟滞退出条件

- 位置：`spec/algorithm_pseudocode.md:81-84`
- 描述：HIGH→NORMAL 退出判断中，实现包含 GPU 显存迟滞检查（`gpu_memory_percent > gpu_high_exit`），伪代码仅检查 memory 和 cpu。
- 影响：文档精度，不影响运行。

### ISSUE-30 [Low] — `_running_estimated_load()` 在 non-dry_run 下被无用调用

- 位置：`resource_scheduler.py:425`
- 描述：`_can_admit` 无条件调用 `_running_estimated_load()`，但 non-dry_run 分支不使用其返回值。
- 影响：性能微损（O(R) 遍历 running 字典），不影响正确性。
- 建议：将调用移入 `if self.config.dry_run:` 分支内。

### ISSUE-31 [Low] — `validate_scheduler_config.py` 忽略命令行参数

- 位置：`qa/validate_scheduler_config.py:10`
- 描述：`CONFIG` 硬编码为 `spec/scheduler_config.example.json`，`sys.argv` 参数被忽略。调用 `python qa/validate_scheduler_config.py some_other.json` 实际仍验证硬编码路径。
- 影响：当用户传入自定义配置路径时不生效。当前使用场景下碰巧路径一致，故无功能缺陷。

---

## 八、全局遗留问题状态

| Issue | 首次发现 | 当前状态 | 备注 |
|-------|:--------:|:--------:|------|
| ISSUE-9（项目方向分裂）| R3 | **待用户决策** | 资源调度 vs 记忆管线，patent/ 仍指向原方案 |
| ISSUE-13（prior_art 虚假核验）| R3 | **仍未处理** | 16 项标记"已核验"无证据 |
| ISSUE-20（旧版 figures/ 残留）| R3-sup | **待验证** | 未观察到清理旧版 CSV/JSON |
| R-04（blocked_total 口径）| R4 / Codex R-04 | **可接受** | 实验脚本已补充 unique_blocked_tasks |
| R-05（任务级 GPU affinity）| Codex R-05 | **后续优化** | 当前 worst-card 策略已足够安全 |
| SUG-8（抢占排序方向）| R4 | **未处理** | 建议项，不阻塞 |
| SUG-9（stuck task 逃逸）| R4 | **未处理** | 建议项，不阻塞 |
| ISSUE-29（伪代码 GPU 迟滞）| R5 | **新发现** | Low |
| ISSUE-30（无用调用）| R5 | **新发现** | Low |
| ISSUE-31（validate 忽略参数）| R5 | **新发现** | Low |

---

## 九、测试覆盖评审

当前 14 个测试：

| # | 测试用例 | 覆盖场景 | 状态 |
|:-:|----------|----------|:----:|
| 1 | test_mode_transition | NORMAL→HIGH→EMERGENCY | ✓ |
| 2 | test_admission_blocked_by_projected_memory | 内存投影阻断 | ✓ |
| 3 | test_emergency_preemption | 紧急抢占 | ✓ |
| 4 | test_batch_projection_prevents_oversubscribe_same_tick | 同 tick 累计投影（不依赖双重计数）| ✓ |
| 5 | test_emergency_cooldown_holds_mode | 冷却期保持 | ✓ |
| 6 | test_timeout_count_once | 超时单次计数（BUG-1 回归）| ✓ |
| 7 | test_raw_emergency_spike_not_masked_by_ema | EMA 不遮蔽 raw 紧急（F-01）| ✓ |
| 8 | test_duplicate_task_id_rejected | 重复 ID 拒绝（F-03）| ✓ |
| 9 | test_invalid_task_spec_rejected | 非法参数拒绝（F-02）| ✓ |
| 10 | test_unknown_config_key_rejected | 未知配置键拒绝（F-04）| ✓ |
| 11 | test_stop_failure_keeps_task_tracked | 终止失败保留跟踪（F-05）| ✓ |
| 12 | test_event_log_is_bounded | 日志上限截断（F-06）| ✓ |
| 13 | test_dry_run_admission_no_double_count_same_tick | **dry_run 无双重计数（F-07）** | ✓ 新增 |
| 14 | test_gpu_monitor_uses_worst_card_for_multi_gpu | **多卡取最高风险（F-08）** | ✓ 新增 |

**仍缺失的测试**（低优先级建议）：
- 迟滞退出数值验证（HIGH → NORMAL 在 hysteresis 区间内保持 HIGH）
- GPU 保护路径的完整 admission + emergency 联动
- 智能回收的 reclaim_needed_mb 目标精确验证
- real-run 模式下 `planned_extra_*` 的 admission 投影验证

---

## 十、Codex 工作效率与质量趋势

| 维度 | R3 (首次) | R3-sup | R4 | R5 (本轮) | 趋势 |
|------|:---------:|:------:|:--:|:---------:|:----:|
| 代码架构 | — | 8/10 | 8/10 | 8/10 | ➡ 稳定 |
| 正确性 | — | 7/10 | 7/10 | **9/10** | ⬆ BUG-2 修复 |
| 可执行性 | — | 9/10 | 9/10 | 9/10 | ➡ 稳定 |
| 测试质量 | — | 6/10 | 8/10 | **9/10** | ⬆ 每个修复都有针对性测试 |
| 文档配套 | — | 8/10 | 6/10 | **8/10** | ⬆ 伪代码重写（残余 ISSUE-29） |
| 安全性 | — | 8/10 | 9/10 | 9/10 | ➡ 稳定 |
| 自检可信度 | 2/10 | — | 8/10 | **9/10** | ⬆ 持续改善 |

**综合进步评价**：

Codex 在本轮展现了高效的闭环修复能力：
1. **响应速度**：R4 评审后快速产出修复，1 个 commit 涵盖全部必修项和建议项
2. **修复质量**：F-07/F-08 修复均为真实有效修复，注释说明清晰，测试覆盖到位
3. **文档同步**：伪代码和数据模型主动重写，而非仅修补
4. **治理意识**：主动回避 `.claude.md` 编码风险，对 ISSUE-9 正确定位为治理决策
5. **自查可信度**：从 R3 的虚假修复（2/10）到 R5 的 8/8 修复全部真实（9/10），进步显著

---

## 十一、评审总结与判定

### 本轮 R4 修复闭环总结

| R4 Issue | 严重程度 | Codex 响应 | Claude R5 验证 | 闭环状态 |
|----------|:--------:|:----------:|:--------------:|:--------:|
| BUG-2 | **必须修复** | F-07 修复 + 测试 | **确认已修复** | ✅ 闭环 |
| ISSUE-21 | 建议修复 | 伪代码重写 | **确认已修复** | ✅ 闭环 |
| ISSUE-22 | 建议修复 | 伪代码重写 | **大部分修复**（残余 ISSUE-29）| ⚠ 近闭环 |
| ISSUE-27 | 建议修复 | F-08 修复 + 测试 | **确认已修复** | ✅ 闭环 |
| ISSUE-28 | 严重 | 回避策略 | **策略合理** | ✅ 闭环 |
| R1 ISSUE-2 | 五轮遗留 | 日志清理 | **确认已修复** | ✅ 闭环 |

### 评审判定：通过（PASS）

**理由**：
1. R4 唯一的必修项 BUG-2 已被正确修复，修复逻辑经数学验证和测试双重确认
2. 全部建议项均已响应，其中 4/5 完全闭环
3. 本轮新发现的 3 个问题（ISSUE-29/30/31）均为 Low 级别，不影响系统正确性和安全性
4. 14/14 测试通过，配置校验通过，结构检查通过
5. 代码零 Critical/High 缺陷

**遗留阻塞项（非代码层面）**：
- ISSUE-9（项目方向分裂）仍需用户决策
- ISSUE-13（prior_art 虚假核验）仍未处理

**建议后续优化**：
- ISSUE-29：补充伪代码 GPU 迟滞条件
- ISSUE-30：优化 `_running_estimated_load()` 调用位置
- ISSUE-31：`validate_scheduler_config.py` 支持命令行参数
- SUG-8/9：考虑抢占排序策略和 stuck task 逃逸机制

---

*评审人：Claude (Opus 4.6)*
*评审时间：2026-02-10 13:00:00 +08:00*
*评审范围：Codex commit `5594b53` 全部变更（10 文件，+842/-210 行）*
*评审判定：**通过（PASS）***
*下次评审触发条件：Codex 下一批提交或用户确认项目方向后*

---

## 附录 A：历史评审汇总

| 评审 | 时间 | 范围 | 判定 | 关键发现 |
|:----:|:----:|------|:----:|----------|
| R1 | 2026-02-09 15:20 | M0 骨架 | Conditional PASS | 5 个 issue |
| R2 | 2026-02-09 16:00 | gptdeepsearch 更新 | — | 3 个 critical issue |
| R3 | 2026-02-10 00:45 | 全量（5 commit + 工作树）| **REJECT** | ISSUE-9 项目方向分裂、ISSUE-12 虚假修复、ISSUE-13 虚假核验 |
| R3-sup | 2026-02-10 01:05 | 资源调度代码质量 | Conditional PASS | BUG-1 timeout 双重计数、ISSUE-18/19/20 |
| R4 | 2026-02-10 11:30 | R3-sup 后全部更新 | Conditional PASS | BUG-2 dry_run 双重计数、ISSUE-21/22/27/28、F-01~F-06 全部确认 |
| **R5** | **2026-02-10 13:00** | **commit 5594b53** | **PASS** | **F-07/F-08 确认、ISSUE-21/22/27/28/ISSUE-2 闭环、ISSUE-29/30/31 新发现（Low）** |

## 附录 B：累计 Bug/Issue 追踪

| ID | 严重程度 | 首次发现 | 修复确认 | 状态 |
|----|:--------:|:--------:|:--------:|:----:|
| BUG-1 | 必修 | R3-sup | R4 ✓ | 已闭环 |
| BUG-2 | 必修 | R4 | **R5 ✓** | **已闭环** |
| ISSUE-2 | 重要 | R1 | **R5 ✓** | **已闭环**（6 轮） |
| ISSUE-9 | 致命 | R3 | — | 待用户决策 |
| ISSUE-10~12 | 严重 | R3 | 方向转换后不适用 | 归档 |
| ISSUE-13 | 严重 | R3 | — | 仍未处理 |
| ISSUE-14~17 | 重要 | R3 | 方向转换后不适用 | 归档 |
| ISSUE-18 | 建议 | R3-sup | R4 ✓ | 已闭环 |
| ISSUE-19 | 建议 | R3-sup | R4 ✓ | 已闭环 |
| ISSUE-20 | 建议 | R3-sup | — | 待验证 |
| ISSUE-21 | 建议 | R4 | **R5 ✓** | **已闭环** |
| ISSUE-22 | 建议 | R4 | **R5 近闭环** | **残余 ISSUE-29** |
| ISSUE-27 | 建议 | R4 | **R5 ✓** | **已闭环** |
| ISSUE-28 | 严重 | R4 | **R5 回避策略** | **已闭环** |
| ISSUE-29 | Low | R5 | — | 新发现 |
| ISSUE-30 | Low | R5 | — | 新发现 |
| ISSUE-31 | Low | R5 | — | 新发现 |
| F-01~F-08 | — | Codex 自查 | R4/R5 全部确认 | 已闭环 |
