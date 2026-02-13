# Technique-Claim Mapping（Resource Scheduler v1）

- Timestamp: 2026-02-11 13:03:10 +08:00
- Owner: Codex (GPT-5)
- Purpose: 将资源调度新版权利要求映射到可执行代码与可复现实验

## 1. 主映射表

| 权利要求点 | 技术特征 | 代码证据 | 测试证据 | 实验证据 |
|---|---|---|---|---|
| C1 | 双视图判定：紧急看 raw，稳态看 EMA | `prototype/resource_scheduler.py:432`, `prototype/resource_scheduler.py:440`, `prototype/resource_scheduler.py:454` | `prototype/tests/test_resource_scheduler.py:213`, `prototype/tests/test_resource_scheduler.py:1028` | `prototype/run_patent_evidence.py:161` |
| C2 | 迟滞退出与冷却控制 | `prototype/resource_scheduler.py:435`, `prototype/resource_scheduler.py:458`, `prototype/resource_scheduler.py:477` | `prototype/tests/test_resource_scheduler.py:155`, `prototype/tests/test_resource_scheduler.py:170` | `prototype/run_patent_evidence.py:161` |
| C3 | 同 tick 累计准入投影 | `prototype/resource_scheduler.py:301`, `prototype/resource_scheduler.py:317`, `prototype/resource_scheduler.py:496`, `prototype/resource_scheduler.py:533` | `prototype/tests/test_resource_scheduler.py:460`, `prototype/tests/test_resource_scheduler.py:1428` | `prototype/run_patent_evidence.py:230` |
| C4 | per-GPU 亲和准入投影（target card） | `prototype/resource_scheduler.py:555`, `prototype/resource_scheduler.py:560`, `prototype/resource_scheduler.py:571` | `prototype/tests/test_resource_scheduler.py:516`, `prototype/tests/test_resource_scheduler.py:623` | `prototype/run_experiments.py` |
| C5 | GPU 热点卡识别 + 亲和性权重回收 | `prototype/resource_scheduler.py:714`, `prototype/resource_scheduler.py:747`, `prototype/resource_scheduler.py:755` | `prototype/tests/test_resource_scheduler.py:975` | `prototype/run_experiments.py` |
| C6 | 归一化双资源回收评分 | `prototype/resource_scheduler.py:744`, `prototype/resource_scheduler.py:759`, `prototype/resource_scheduler.py:765` | `prototype/tests/test_resource_scheduler.py:1094` | `prototype/run_experiments.py` |
| C7 | 双目标回收停止（内存+GPU） | `prototype/resource_scheduler.py:791`, `prototype/resource_scheduler.py:793` | `prototype/tests/test_resource_scheduler.py:975` | `prototype/run_experiments.py` |
| C8 | 终止失败逃逸与强制移除 | `prototype/resource_scheduler.py:656`, `prototype/resource_scheduler.py:665`, `prototype/resource_scheduler.py:675` | `prototype/tests/test_resource_scheduler.py:905` | 无（行为级测试为主） |
| C9 | 阻断事件与唯一任务阻断计数分离 | `prototype/resource_scheduler.py:95`, `prototype/resource_scheduler.py:817`, `prototype/resource_scheduler.py:820` | `prototype/tests/test_resource_scheduler.py:303` | `prototype/run_experiments.py` |
| C10 | per-GPU 投影相较总量投影可降低误阻断 | `prototype/resource_scheduler.py:555`, `prototype/resource_scheduler.py:562`, `prototype/resource_scheduler.py:564` | `prototype/tests/test_resource_scheduler.py:516`, `prototype/tests/test_advanced_research.py:15` | `prototype/run_advanced_research.py`（P-04） |
| C11 | 归一化抢占评分相对随机/原始MB基线更高效 | `prototype/resource_scheduler.py:744`, `prototype/resource_scheduler.py:759`, `prototype/resource_scheduler.py:765` | `prototype/tests/test_resource_scheduler.py:1094`, `prototype/tests/test_advanced_research.py:21` | `prototype/run_advanced_research.py`（P-05） |
| C12 | 资源估算自校准：按画像 EMA 更新并在提交时保守放大估算 | `prototype/resource_scheduler.py:845`, `prototype/resource_scheduler.py:862`, `prototype/resource_scheduler.py:906` | `prototype/tests/test_resource_scheduler.py:1482`, `prototype/tests/test_resource_scheduler.py:1517` | `prototype/run_advanced_research.py`（可配合真机基线长期运行验证） |

## 2. 消融结论（可复核）

1. P-02（双视图）：
   - `dual_view_raw_plus_ema` 延迟 0 tick；
   - `ema_only_alpha_0_3_no_raw_bypass` 延迟 3 ticks。  
   证据：`figures/patent_evidence_metrics.json`
2. P-03（同 tick 累计）：
   - 有累计投影：2 任务，90.8906%（未越线）；
   - 无累计投影：4 任务，100.6562%（越线）。  
   证据：`figures/patent_evidence_metrics.json`

## 3. 审核清单

- [x] 每个关键权利点有代码锚点
- [x] 每个关键权利点有测试或实验锚点
- [x] 行号基于当前工作树复核
- [x] 结论与 `patent/权利要求书_资源调度_v1.md` 术语一致
