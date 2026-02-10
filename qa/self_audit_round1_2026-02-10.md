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
  - `prototype/resource_scheduler.py:624`
  - `prototype/resource_scheduler.py:635`
  - `prototype/resource_scheduler.py:641`
  - `prototype/resource_scheduler.py:643`
  - `prototype/resource_scheduler.py:645`
  - `prototype/resource_scheduler.py:647`
  - `qa/validate_scheduler_config.py:61`
  - `qa/validate_scheduler_config.py:66`
- 回归测试：`prototype/tests/test_resource_scheduler.py:167`

### F-05 [Medium] 终止失败场景可能留存孤儿进程
- 风险描述：原实现在 kill 异常时吞掉错误并移除跟踪，可能导致进程仍在运行但调度器误判已停止。
- 修复前位置：`prototype/resource_scheduler.py:523`, `prototype/resource_scheduler.py:533`, `prototype/resource_scheduler.py:536`
- 修复动作：`_stop_task` 改为返回布尔结果；仅在确认停止后才移出 `running`，失败时记录 `TASK_STOP_FAILED`。
- 修复后证据：`prototype/resource_scheduler.py:523`, `prototype/resource_scheduler.py:543`, `prototype/resource_scheduler.py:554`
- 回归测试：`prototype/tests/test_resource_scheduler.py:181`

### F-06 [Medium] 事件日志无上限，长时运行有内存增长风险
- 风险描述：`events` 持续追加会推高调度器自身内存占用，和“防爆”目标冲突。
- 修复前位置：`prototype/resource_scheduler.py:591`
- 修复动作：新增 `max_event_log_entries`，超限后按 FIFO 截断。
- 修复后证据：`prototype/resource_scheduler.py:72`, `prototype/resource_scheduler.py:591`, `prototype/resource_scheduler.py:647`
- 配置同步：`spec/scheduler_config.example.json:22`, `qa/validate_scheduler_config.py:54`, `qa/validate_scheduler_config.py:78`
- 回归测试：`prototype/tests/test_resource_scheduler.py:220`

### F-07 [Critical] dry_run 模式同 tick 已启动任务双重计数
- 风险描述：`_can_admit` 在 dry_run 下同时叠加 `planned_extra_*` 与 `_running_estimated_load()`，导致同 tick 已启动任务被重复计入，错误阻断后续任务。
- 修复前位置：`prototype/resource_scheduler.py:425`, `prototype/resource_scheduler.py:429`
- 修复动作：dry_run 路径仅使用 `running_estimated_load`；real-run 路径使用 `planned_extra_*`。
- 修复后证据：`prototype/resource_scheduler.py:413`, `prototype/resource_scheduler.py:430`
- 回归测试：`prototype/tests/test_resource_scheduler.py:242`

### F-08 [Medium] 多 GPU 只监控首卡
- 风险描述：原实现读取 `nvidia-smi` 第一行，可能漏掉其他 GPU 的过载风险。
- 修复前位置：`prototype/resource_scheduler.py:161`
- 修复动作：解析全部 GPU 行，按显存占比最高卡作为风险判定输入。
- 修复后证据：`prototype/resource_scheduler.py:148`, `prototype/resource_scheduler.py:177`
- 回归测试：`prototype/tests/test_resource_scheduler.py:259`

### F-09 [Low] 伪代码遗漏 GPU 迟滞退出条件
- 风险描述：伪代码 HIGH->NORMAL 退出条件仅含内存/CPU，遗漏 GPU 迟滞条件，导致文档与实现不一致。
- 修复动作：在 Section 2 增加 GPU 迟滞退出分支。
- 修复后证据：`spec/algorithm_pseudocode.md:81`

### F-10 [Low] non-dry_run 无用调用 `_running_estimated_load()`
- 风险描述：`_can_admit` 在 non-dry_run 路径执行 O(R) 计算但结果不使用，造成可避免开销。
- 修复动作：将 `_running_estimated_load()` 调用移动到 dry_run 分支内部。
- 修复后证据：`prototype/resource_scheduler.py:429`
- 回归测试：`prototype/tests/test_resource_scheduler.py:273`

### F-11 [Low] 配置校验脚本忽略命令行路径
- 风险描述：脚本固定读取默认配置，用户传入路径时无效。
- 修复动作：新增 `_resolve_config_path(sys.argv)`，支持可选参数路径与 usage 检查。
- 修复后证据：`qa/validate_scheduler_config.py:18`
- 回归测试：`prototype/tests/test_resource_scheduler.py:355`

### F-12 [Medium] 抢占排序策略硬编码
- 风险描述：紧急抢占固定按“旧任务优先”排序，缺乏策略可配置性，难以适配不同业务偏好。
- 修复动作：新增配置 `preempt_sort_key`，支持 `oldest_first/newest_first`。
- 修复后证据：
  - `prototype/resource_scheduler.py:64`
  - `prototype/resource_scheduler.py:583`
  - `prototype/resource_scheduler.py:669`
  - `qa/validate_scheduler_config.py:47`
  - `qa/validate_scheduler_config.py:73`
  - `spec/scheduler_config.example.json:16`
- 回归测试：
  - `prototype/tests/test_resource_scheduler.py:273`
  - `prototype/tests/test_resource_scheduler.py:285`

### F-13 [Medium] 不可终止任务缺少逃逸机制
- 风险描述：任务持续 stop 失败会长期占据 `running`，影响调度稳定性。
- 修复动作：新增 `stuck_task_timeout_sec`，达到阈值后强制移出并发出 `TASK_STUCK_REMOVED` 事件。
- 修复后证据：
  - `prototype/resource_scheduler.py:66`
  - `prototype/resource_scheduler.py:97`
  - `prototype/resource_scheduler.py:557`
  - `prototype/resource_scheduler.py:561`
  - `qa/validate_scheduler_config.py:49`
  - `qa/validate_scheduler_config.py:81`
  - `spec/scheduler_config.example.json:18`
- 回归测试：`prototype/tests/test_resource_scheduler.py:311`

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
- [x] 伪代码与实现一致性：补齐 GPU 迟滞退出条件。
- [x] non-dry_run 性能细节：移除无用负载估算调用。
- [x] 配置校验脚本可用性：支持命令行路径参数。
- [x] 抢占策略可配置：支持 oldest/newest 两种排序键。
- [x] stuck task 逃逸机制：超时强制移出并记录审计事件。
- [x] 回归测试：新增 13 个用例，全部通过。
- [x] 结构检查：通过。
- [x] 配置检查：通过。
- [x] 旧功能回归：原 6 个测试保持通过。

## 6. 复验命令与结果
```powershell
python -m unittest discover -s prototype/tests -p "test_*.py"
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```
结果：19/19 测试通过（含 ISSUE-29/30/31 与 R6 回归测试），配置校验 PASS，结构检查 PASS。

## 7. 供 Claude 下轮对比的基线 ID
- 已修复：`F-01`, `F-02`, `F-03`, `F-04`, `F-05`, `F-06`, `F-07`, `F-08`, `F-09`, `F-10`, `F-11`, `F-12`, `F-13`
- 待复核：`R-04`, `R-05`
