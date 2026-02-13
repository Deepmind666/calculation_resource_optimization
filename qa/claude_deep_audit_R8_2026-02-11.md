# Claude 深度自查 + 专利前景诚实评估

- 时间戳：2026-02-11 01:30 +08:00
- 审查人：Claude (Opus 4.6)
- 范围：全量代码漏洞审查 + F-17 验证 + ISSUE-32/33/34/35 闭环验证 + 发明专利前景评估

---

## 第一部分：代码漏洞深度审查

### 验证状态
- 38/38 测试通过
- 配置校验 PASS
- 结构检查 PASS
- run_experiments.py / run_patent_evidence.py 执行通过

### BUG-3 [Critical] `_smooth_snapshot` 丢失 `gpu_cards`，GPU affinity 在生产配置下必定失败

**严重程度**：Critical（F-17 整个功能在生产配置下失效）

**位置**：`prototype/resource_scheduler.py:369-383`

**复现路径**：
1. 设置 `ema_alpha=0.6`（生产默认配置）
2. 提交一个带 `target_gpu_index=0` 的任务
3. `tick()` → `_smooth_snapshot()` 构造新 `ResourceSnapshot` 时**没有传入 `gpu_cards`**
4. `_can_admit()` 收到的 snapshot 中 `gpu_cards=None`
5. `cards = s.gpu_cards or []` → `[]`
6. `target(0) >= len([])=0` → True → 返回 `"target gpu unavailable"`

**根因**：
```python
# 第 369-383 行：gpu_cards 参数未传递
smoothed = ResourceSnapshot(
    timestamp=raw.timestamp,
    cpu_percent=blend(...),
    ...
    gpu_memory_total_mb=raw.gpu_memory_total_mb or prev.gpu_memory_total_mb,
    # 缺少: gpu_cards=raw.gpu_cards   <--- BUG
)
```

**为什么测试没抓到**：
全部 GPU affinity 测试都用 `ema_alpha=1.0`，此时 `_smooth_snapshot` 直接返回 `raw`（第 351-353 行），不走构造新对象的路径，`gpu_cards` 不会丢失。生产配置 `ema_alpha=0.6` 未被任何 GPU 测试覆盖。

**修复建议**：在 `_smooth_snapshot` 第 380 行后加 `gpu_cards=raw.gpu_cards`，并补一个 `ema_alpha<1.0` 的 GPU affinity 测试。

---

### 逐路径审查结果

| 路径 | 审查结果 | 备注 |
|---|---|---|
| 模式判定 (`_evaluate_mode`) | ✓ 无漏洞 | raw→紧急, smoothed→稳态, GPU迟滞, 冷却机制均正确 |
| 准入控制 (`_can_admit`) | ⚠ BUG-3 | 非 GPU affinity 路径无漏洞；GPU affinity 在 ema_alpha<1.0 时失效 |
| dry_run / real 分叉 | ✓ 无漏洞 | F-07 修复稳固，per-GPU budget 正确分离 |
| 堆优先级一致性 | ✓ 无漏洞 | seq 唯一保证无 TaskSpec 比较；blocked 重推后堆不变 |
| 进程生命周期 | ✓ 无漏洞 | terminate→kill→stuck 逐级升级正确 |
| 事件日志上限 | ✓ 无漏洞 | FIFO 截断正常 |
| blocked 指标分离 | ✓ 无漏洞 | event/unique 计数正确，完成后释放 |
| EMERGENCY 待排观测 | ✓ 无漏洞 | 每 tick emit TASK_BLOCKED（设计选择：高频事件） |
| 配置校验 | ✓ 无漏洞 | memory/cpu/gpu 阈值关系全覆盖 |
| 浮点精度 | ✓ 无问题 | 百分比级别精度，`>=` 比较安全 |

### 低优先级观察

| 编号 | 描述 | 严重度 |
|---|---|---|
| OBS-1 | EMERGENCY 模式每 tick 对所有 pending 发 TASK_BLOCKED，长期紧急状态会导致 `blocked_total` 极大 | Low |
| OBS-2 | dry_run 下 GPU affinity 投影使用全局 running_gpu_est 而非 per-card 分解，过于保守 | Low |
| OBS-3 | `_preempt_low_priority` 的排序 key 使用 `sort(reverse=True)`，高 priority 值（低重要性）排前面，逻辑正确但命名可能令人困惑 | Info |

---

## 第二部分：F-17 / ISSUE 闭环验证

### F-17 GPU Affinity 准入预测

**实现验证**（排除 BUG-3 的路径问题，逻辑本身正确）：
- `TaskSpec.target_gpu_index` 字段正确添加 ✓
- `ResourceSnapshot.gpu_cards` 正确承载每卡明细 ✓
- `_sample_gpu` 输出 cards 列表 + 保持聚合字段 ✓
- `_can_admit` per-card 投影逻辑正确 ✓（在 `ema_alpha=1.0` 下）
- 任务输入校验新增负值 affinity 检查 ✓
- `NoCumulativeProjectionScheduler._can_admit` 正确透传新参数签名 ✓

**测试覆盖**：
- `test_gpu_affinity_uses_target_card_projection` (line 462) ✓
- `test_gpu_affinity_rejects_unavailable_target` (line 501) ✓
- `test_real_run_gpu_projection_uses_per_gpu_planned_budget` (line 529) ✓
- `test_real_run_unbound_gpu_projection_remains_conservative` (line 564) ✓
- `test_invalid_task_spec_rejected` 扩展 (line 233) ✓
- `test_gpu_monitor_uses_worst_card_for_multi_gpu` 扩展 (line 436) ✓

**判定：F-17 逻辑正确，但被 BUG-3 阻断了生产可用性。需先修复 BUG-3。**

### ISSUE 闭环

| ISSUE | 修复 | 验证 |
|---|---|---|
| ISSUE-32 | `_finish_task`/`_stop_task` 中 `_blocked_task_ids.discard()` | `test_blocked_task_tracking_released_after_completion` ✓ |
| ISSUE-33 | `data_model.md` 补齐 `gpu_cards` / `target_gpu_index` | 文档与代码一致 ✓ |
| ISSUE-34 | `technique_claim_mapping` 行号更新 | 抽查 C1 `:388` → `_evaluate_mode` 附近 ✓ |
| ISSUE-35 | EMERGENCY 模式下 pending 任务 emit TASK_BLOCKED | `test_emergency_pending_tasks_emit_per_task_block_events` ✓ |

---

## 第三部分：发明专利前景诚实评估

### 当前可申请专利点

| ID | 技术特征 | 消融证据 | 效果量化 |
|---|---|---|---|
| P-02 | 双视图模式判定（raw→紧急 + EMA→稳态） | ✓ 有对照实验 | 响应延迟：0 vs 3 ticks |
| P-03 | 同 tick 累计投影准入 | ✓ 有对照实验 | 超发率：0% vs 50% |
| F-17 | 任务级 GPU 亲和性准入投影 | 部分（仅逻辑正确，有 BUG-3） | 定性：减少跨卡误阻断 |

### 严重风险点

#### 风险 1：Prior Art 索引完全不对口（致命）

`prior_art/prior_art_index.md` 的 16 项全部是旧方向（语义记忆聚类/摘要），**没有一项涉及资源调度**。

资源调度领域的已知先行技术（从我的知识库）：

| 参考 | 相关技术 | 与本项目重叠 |
|---|---|---|
| Kubernetes Eviction Manager | 多级阈值（soft/hard eviction）+ 资源预留 | 与 NORMAL/HIGH/EMERGENCY 三级直接类似 |
| Linux PSI (Pressure Stall Info) | 多级资源压力检测 | 与模式判定直接类似 |
| Google Borg (EuroSys 2015) | 优先级抢占 + admission control + 资源投影 | 与 P-03 概念直接重叠 |
| YARN Capacity Scheduler | 资源预留 + admission based on available capacity | 与准入控制直接重叠 |
| 控制论/信号处理 | EMA 平滑 + 原始信号阈值检测 | 与 P-02 原理直接重叠 |

**结论**：在没有做过资源调度领域正式检索的情况下，无法判断新颖性。

#### 风险 2：单项技术创造性不足

| 技术 | 已知程度 | 审查员可能的驳回理由 |
|---|---|---|
| P-02 (raw+EMA双视图) | 高 | "使用原始信号检测突变、使用平滑信号检测趋势"是控制论基本方法，对本领域技术人员显而易见 |
| P-03 (同tick累计投影) | 高 | "在批量准入时累计已提交资源"是调度器设计的标准做法（Kubernetes 的 ResourceQuota 即是类似机制） |
| 三级模式 + 迟滞 | 高 | 三级状态机 + 迟滞是电子工程 / 控制论经典模式 |

#### 风险 3：ISSUE-13 仍未解决

Prior art 的 16 项"已核验"标记至今没有任何核验证据。在没有真实核验的情况下，novelty assessment 不可信。

#### 风险 4：patent/ 目录内容是旧方向

`patent/权利要求书.md` 等全部文档仍是"语义记忆碎片聚类压缩"方向，与当前资源调度实现完全不匹配。

### 中国发明专利三要件评估

| 要件 | 评估 | 概率 |
|---|---|---|
| 新颖性（Novelty） | 具体组合可能新颖（多个已知技术的特定搭配），但单一参考文献可能已覆盖 | 40-50% |
| 创造性（Inventive Step） | **最大风险**。P-02 和 P-03 各自都是本领域常规技术手段，审查员很可能以"对本领域技术人员显而易见"驳回 | 15-25% |
| 实用性（Utility） | 完全满足 | 100% |

### 综合概率估算

**发明专利授权概率：15-30%**

（如果是实用新型专利，概率约 75-85%，但保护力度弱得多）

### 提升专利授权概率的具体建议

1. **做真正的资源调度领域 prior art 检索**（最重要）
   - 搜索 CPC 分类 G06F 9/50（资源调度）、G06F 11/34（性能监控）
   - 搜索关键词组合："admission control" + "memory projection" + "multi-level scheduling"
   - 确认是否有先行技术同时包含：EMA+raw 双视图 + 同 tick 累计投影 + 三级模式 + per-GPU affinity

2. **缩窄权利要求到非显而易见的组合**
   - 不要单独申请 P-02 或 P-03
   - 申请**整体方案**：三级模式切换 + 双视图判定 + 同 tick per-GPU 累计投影 + 迟滞冷却 + 智能回收目标
   - 写成"一种基于双视图多模式的计算资源动态调度方法"，将多个技术特征组合为一个不可分拆的权利要求

3. **增加差异化特征**
   - per-GPU affinity admission（修复 BUG-3 后）是一个较好的差异点
   - 考虑增加"任务级资源画像学习"功能（基于历史运行校正估算值），这在现有调度器中较少见
   - 考虑增加"跨资源维度联合投影"（同时考虑 memory + CPU + GPU 的交叉约束），目前很多调度器是单维度判断

4. **请专利代理人/律师审阅**
   - 专利文本撰写质量对授权影响极大
   - 权利要求的措辞、从属关系、独立权利要求的保护范围都需要专业把控

5. **重写 patent/ 目录**
   - 当前全部是旧方向文本，需要从头写

---

## 第四部分：行动项优先级

| 优先级 | 事项 | 原因 |
|---|---|---|
| **P0 阻塞** | 修复 BUG-3（`_smooth_snapshot` 丢失 `gpu_cards`） | F-17 在生产配置下完全失效 |
| **P0 阻塞** | 补 `ema_alpha<1.0` 的 GPU affinity 测试 | 防止同类 regression |
| **P1 重要** | 做资源调度领域 prior art 正式检索 | 没有这个就无法评估新颖性 |
| **P1 重要** | 重写 patent/ 目录为资源调度方向 | 当前内容完全不匹配 |
| **P2 建议** | 增加差异化特征（资源画像学习 / 跨维度联合投影） | 提升创造性 |
| **P2 建议** | 请专利代理人审阅 | 专业文本撰写 |

---

## 总结

**代码质量**：在修复 BUG-3 之前，代码处于"除一个 Critical bug 外成熟稳定"状态。BUG-3 是 F-17（GPU affinity）与 EMA 平滑之间的集成遗漏，所有测试用 `ema_alpha=1.0` 导致未被发现。

**发明专利前景**：**概率不高（15-30%）**，主要瓶颈在于：
1. 尚未做过资源调度领域的 prior art 检索
2. P-02/P-03 各自都是本领域常规技术
3. patent/ 目录内容与实现不匹配

**核心建议**：如果要走发明专利路线，需要：(1) 先做领域检索确认新颖性，(2) 缩窄到不可分拆的技术组合方案，(3) 请专利代理人撰写权利要求。如果时间/成本有限，实用新型专利是更现实的选择。

---

*审查人：Claude (Opus 4.6) — 所有代码断言均经逐行追踪验证*
