# prototype

本目录是“资源调度防爆”原型实现。

核心文件：
1. `resource_scheduler.py`：资源监控、模式判定、接纳控制、紧急回收。
2. `main.py`：演示入口（默认 dry-run，安全）。
3. `run_experiments.py`：多场景实验并输出 CSV/JSON。
4. `tests/test_resource_scheduler.py`：单元测试。

## 快速运行
```powershell
cd prototype
python main.py --ticks 12
python run_experiments.py
python -m unittest discover -s tests -p "test_*.py"
cd ..
```

## 安全说明
1. `main.py` 默认 `dry-run`，不启动真实子进程。
2. 需要真实执行时再加 `--real-run`，且建议先小规模验证。
