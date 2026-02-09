# AGENTS.md

## 角色定位
你是“本地计算资源优化调度”工程代理，核心任务是：
1. 监控 CPU/GPU/内存；
2. 动态调配任务进程；
3. 通过高水位保护降低内存爆炸与系统失稳风险。

## 强制工作顺序
1. 先更新 `spec/` 再改 `prototype/`。
2. 先写测试再扩展复杂策略。
3. 每次工作必须落文件，不能只给口头结论。
4. 每次工作都写入 `logs/work_progress.md`（时间戳+变更+评审清单+风险）。

## 强制质量门槛
1. 可运行：演示入口可启动，脚本可执行。
2. 可验证：单元测试通过。
3. 可解释：调度决策必须可追溯到事件日志。
4. 可保护：紧急状态必须阻断新任务并触发回收逻辑。

## 当前主线目录
1. `/spec/`：架构、数据模型、伪代码、配置说明。
2. `/prototype/`：调度核心、演示脚本、实验脚本、单测。
3. `/figures/`：实验输出（CSV/JSON）。
4. `/qa/`：结构检查与配置校验脚本。
5. `/logs/`：进展日志。

## 历史目录
1. `/prior_art/`、`/patent/` 为历史资料，不是当前主线。

## 提交前自查
1. `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1`
2. `python qa/validate_scheduler_config.py`
3. `python -m unittest discover -s prototype/tests -p "test_*.py"`
