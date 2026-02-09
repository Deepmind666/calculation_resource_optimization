# MASTER BRIEF：本地计算资源动态调度与防爆保护

## 一句话目标
根据 CPU / GPU / 内存实时状态，动态调配任务进程，尽量避免本地电脑出现内存爆炸、卡死、被迫重启。

## 核心功能
1. 实时监控：CPU、内存、Swap、GPU 显存。
2. 动态调度：任务接纳、排队、并发调节。
3. 安全保护：高水位限流、紧急模式回收低优先级任务。
4. 可追溯：每次调度决策都可记录和复盘。

## 状态分级
1. NORMAL：资源健康，按最大并发执行。
2. HIGH：资源偏高，降低并发并限制低优先级任务。
3. EMERGENCY：资源危险，停止新任务并触发回收。

## 最小可交付
1. `spec/architecture.md`：完整架构说明。
2. `prototype/resource_scheduler.py`：调度核心实现。
3. `prototype/main.py`：演示入口。
4. `prototype/run_experiments.py`：实验指标输出（CSV/JSON）。
5. `prototype/tests/test_resource_scheduler.py`：单元测试。

## 质量门槛
1. 代码可运行，单测可通过。
2. 调度日志能解释“为什么阻断/为什么回收”。
3. 紧急模式下必须阻断新任务并回收低优先级任务。
4. 每次进展必须写入 `logs/work_progress.md`（时间戳+清单+风险）。
