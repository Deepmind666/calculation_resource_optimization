# prototype

存放可运行原型、单元测试、实验脚本和结果生成脚本。

最低交付：
- `main.py` 或等价入口
- `tests/`
- `run_experiments.py`

当前状态（Phase 1）：
- `memory_pipeline.py`：最小管线实现（采集、并簇、冲突分叉、槽位覆盖校验、审计报告）。
- `main.py`：可直接运行的演示入口。
- `tests/test_memory_pipeline.py`：单元测试。
- `run_experiments.py`：合成数据实验与指标导出（CSV/JSON）。

运行方式：
```powershell
cd prototype
python main.py
python -m unittest discover -s tests -p \"test_*.py\"
python run_experiments.py
```
