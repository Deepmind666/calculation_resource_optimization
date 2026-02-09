# 实验报告（Phase 1）

更新时间：2026-02-09（UTC+08:00）

## 复现命令
```powershell
cd prototype
python run_experiments.py
cd ..
```

## 产物
- `figures/experiment_metrics.csv`
- `figures/experiment_metrics.json`

## 指标说明
- `token_compression_rate`：压缩率（1 - 摘要 token / 原始 token）。
- `conflict_retention_rate`：冲突保留率（检测到冲突的簇数 / 预期冲突数）。
- `preference_compliance_rate`：偏好合规率（满足必选槽位覆盖阈值的比例）。
- `runtime_ms`：单轮处理耗时（毫秒）。

## 当前结果解读
1. 当前实现为最小原型，使用轻量哈希向量和规则冲突检测，指标用于验证流程连通性，不代表最终性能上限。
2. 下一阶段应替换为更强嵌入模型与语义冲突检测器，并扩展数据规模后再评估。
