# 自查漏洞报告 R1（资源调度主线）

- 时间戳：2026-02-10 10:31:36 +08:00
- 执行人：Codex (GPT-5)
- 基线版本：`45252c1`（本报告含未提交修复）
- 审计目标：在下一轮 Claude 评审前，先完成一次可复现的内部漏洞自查与修复闭环。

## 1. 审计范围
- `prototype/resource_scheduler.py`
- `prototype/tests/test_resource_scheduler.py`
- `qa/validate_scheduler_config.py`

## 2. 审计方法
1. 静态代码审阅（模式切换、准入控制、抢占、配置加载、异常处理）。
2. 行为回归测试（`unittest` + 配置校验 + 结构校验）。
3. 漏洞分级（Critical/High/Medium）并形成可对比 ID。

## 3. 发现与处置（已修复）

### F-01 [Critical] EMA 平滑导致瞬时紧急峰值漏检
- 风险描述：模式判定仅使用平滑值，可能把真实瞬时尖峰（如内存 99%）误判为 `NORMAL/HIGH`，导致保护动作延迟。
- 修复前位置：`prototype/resource_scheduler.py:209`, `prototype/resource_scheduler.py:336`
- 修复动作：紧急判定改为优先读取原始采样（raw），平滑值只用于非紧急稳定控制。
- 修复后证据：`prototype/resource_scheduler.py:209`, `prototype/resource_scheduler.py:336`, `prototype/resource_scheduler.py:344`
- 回归测试：`prototype/tests/test_resource_scheduler.py:140`

### F-02 [High] 缺少任务输入校验，允许负估值/非法字段进入调度
- 风险描述：负 `estimated_mem_mb` 等输入可绕过准入约束，造成错误放行或风险评估失真。
- 修复前位置：`prototype/resource_scheduler.py:193`（无参数校验）
- 修复动作：新增 `_validate_task_spec`，校验 `task_id/priority/command/estimated_*/max_runtime_sec/dry_run_ticks`。
- 修复后证据：`prototype/resource_scheduler.py:194`, `prototype/resource_scheduler.py:563`
- 回归测试：`prototype/tests/test_resource_scheduler.py:155`

### F-03 [High] 重复 task_id 可导致运行态跟踪冲突
- 风险描述：重复 `task_id` 可能覆盖 `running` 字典中的运行实例，产生不可控行为。
- 修复前位置：`prototype/resource_scheduler.py:193`
- 修复动作：新增 `_pending_task_ids` 跟踪集合，提交阶段拒绝重复 ID。
- 修复后证据：`prototype/resource_scheduler.py:182`, `prototype/resource_scheduler.py:195`
- 回归测试：`prototype/tests/test_resource_scheduler.py:147`

### F-04 [Medium] 配置未知键静默忽略，易掩盖参数拼写错误
- 风险描述：错误配置键被忽略后系统继续用默认值运行，用户会误以为配置生效。
- 修复动作：`load_scheduler_config` 遇未知键直接抛错，并补齐关键边界校验。
- 修复后证据：
  - `prototype/resource_scheduler.py:591`
  - `prototype/resource_scheduler.py:602`
  - `prototype/resource_scheduler.py:608`
  - `prototype/resource_scheduler.py:610`
  - `prototype/resource_scheduler.py:612`
  - `qa/validate_scheduler_config.py:51`
  - `qa/validate_scheduler_config.py:56`
- 回归测试：`prototype/tests/test_resource_scheduler.py:162`

### F-05 [Medium] 终止失败场景可能留存孤儿进程
- 风险描述：原实现在 kill 异常时吞掉错误并移除跟踪，可能导致进程仍在运行但调度器误判已停止。
- 修复前位置：`prototype/resource_scheduler.py:504`, `prototype/resource_scheduler.py:514`, `prototype/resource_scheduler.py:516`
- 修复动作：`_stop_task` 改为返回布尔结果；仅在确认停止后才移出 `running`，失败时记录 `TASK_STOP_FAILED`。
- 修复后证据：`prototype/resource_scheduler.py:504`, `prototype/resource_scheduler.py:524`, `prototype/resource_scheduler.py:535`
- 回归测试：`prototype/tests/test_resource_scheduler.py:177`

### F-06 [Medium] 事件日志无上限，长时运行有内存增长风险
- 风险描述：`events` 持续追加会推高调度器自身内存占用，和“防爆”目标冲突。
- 修复前位置：`prototype/resource_scheduler.py:572`
- 修复动作：新增 `max_event_log_entries`，超限后按 FIFO 截断。
- 修复后证据：`prototype/resource_scheduler.py:72`, `prototype/resource_scheduler.py:572`, `prototype/resource_scheduler.py:627`
- 配置同步：`spec/scheduler_config.example.json:22`, `qa/validate_scheduler_config.py:44`, `qa/validate_scheduler_config.py:69`
- 回归测试：`prototype/tests/test_resource_scheduler.py:216`

### F-07 [Critical] dry_run 模式同 tick 已启动任务双重计数
- 风险描述：`_can_admit` 在 dry_run 下同时叠加 `planned_extra_*` 与 `_running_estimated_load()`，导致同 tick 已启动任务被重复计入，错误阻断后续任务。
- 修复前位置：`prototype/resource_scheduler.py:414`, `prototype/resource_scheduler.py:417`
- 修复动作：dry_run 路径仅使用 `running_estimated_load`；real-run 路径使用 `planned_extra_*`。
- 修复后证据：`prototype/resource_scheduler.py:413`, `prototype/resource_scheduler.py:430`
- 回归测试：`prototype/tests/test_resource_scheduler.py:240`

### F-08 [Medium] 多 GPU 只监控首卡
- 风险描述：原实现读取 `nvidia-smi` 第一行，可能漏掉其他 GPU 的过载风险。
- 修复前位置：`prototype/resource_scheduler.py:161`
- 修复动作：解析全部 GPU 行，按显存占比最高卡作为风险判定输入。
- 修复后证据：`prototype/resource_scheduler.py:148`, `prototype/resource_scheduler.py:177`
- 回归测试：`prototype/tests/test_resource_scheduler.py:257`

## 4. 剩余风险（当前非阻塞）

### R-04 [Low] `blocked_total` 仍是“事件次数”口径
- 位置：`prototype/resource_scheduler.py:255`
- 说明：该指标代表阻断事件，不是唯一任务数；虽然实验脚本已补充 `unique_blocked_tasks`，但主指标名仍可能被误读。
- 建议：后续考虑拆分 `blocked_event_total` 与 `blocked_task_total`。

### R-05 [Low] 多 GPU 仍未区分“任务绑定显卡”
- 位置：`prototype/resource_scheduler.py:177`
- 说明：当前已改为按最高风险卡判定，但仍未基于任务实际绑定卡做精确投影。
- 建议：后续引入任务级 GPU affinity 字段，并按目标卡做 admission 预测。

## 5. 完整代码审核清单（本轮执行状态）
- [x] 模式切换：紧急阈值判定不被平滑延迟。
- [x] 准入控制：同 tick 累计预算仍生效，且参数输入合法。
- [x] 数据一致性：禁止活动队列/运行集重复 task_id。
- [x] 配置可靠性：未知键失败、关键阈值边界失败。
- [x] 进程终止可靠性：终止失败不再丢失跟踪。
- [x] 事件日志上限：具备可配置截断机制。
- [x] dry_run 计数正确性：同 tick 不再双重计数。
- [x] 多 GPU 防护视角：按风险最高卡判定。
- [x] 回归测试：新增 8 个用例，全部通过。
- [x] 结构检查：通过。
- [x] 配置检查：通过。
- [x] 旧功能回归：原 6 个测试保持通过。

## 6. 复验命令与结果
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```
结果：14/14 测试通过，配置校验 PASS，结构检查 PASS。

## 7. 供 Claude 下轮对比的基线 ID
- 已修复：`F-01`, `F-02`, `F-03`, `F-04`, `F-05`, `F-06`, `F-07`, `F-08`
- 待复核：`R-04`, `R-05`
