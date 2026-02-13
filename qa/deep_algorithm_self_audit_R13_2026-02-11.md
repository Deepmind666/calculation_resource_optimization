# Deep Algorithm Self Audit — R13 (Prior Art + Patent Pack)

- Timestamp: 2026-02-11 13:08:41 +08:00
- Executor: Codex (GPT-5)
- Scope: 专利前置材料重建（prior art / claim chart / 新版权利要求与说明书 / 路线决策）

## 1. 本轮目标

1. 把 `prior_art/` 从旧方向补到资源调度方向。
2. 产出与当前代码一致的新版权利要求与说明书草案。
3. 给出“下一步怎么申报”的可执行路线，而不是泛泛建议。

## 2. 自查方法

1. 一致性自查：
   - 检查权利要求术语是否和代码术语一致（raw/EMA、per-GPU、同 tick 累计投影、定向抢占）。
2. 证据自查：
   - 检查 claim mapping 中的代码行号是否有效。
3. 可执行性自查：
   - 执行测试、配置校验、结构检查、证据脚本、实验脚本。

## 3. 自查结果

### 3.1 一致性

- 结果：通过。  
- 证据文件：
  - `patent/权利要求书_资源调度_v1.md`
  - `patent/说明书_资源调度_v1.md`
  - `qa/technique_claim_mapping_resource_scheduler_v1_2026-02-11.md`

### 3.2 行号映射

- 结果：通过（`CLAIM_MAPPING_LINE_CHECK_PASS`）。
- 检查对象：
  - `qa/technique_claim_mapping_resource_scheduler_v1_2026-02-11.md`
  - `prior_art/resource_scheduler_claim_chart.md`

### 3.3 运行验证

- `python -m unittest discover -s prototype/tests -p "test_*.py"`：`51/51 OK`
- `python qa/validate_scheduler_config.py spec/scheduler_config.example.json`：PASS
- `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1`：PASS
- `python prototype/run_patent_evidence.py`：执行成功并生成 `figures/patent_evidence_metrics.*`
- `python prototype/run_experiments.py`：执行成功并生成 `figures/scheduler_experiment_metrics.*`

## 4. 本轮发现的问题与处理

1. 映射行号核验脚本首次执行失败（PowerShell 变量拼接语法问题）。
   - 处理：修正字符串插值后重跑，已通过。
2. 未发现代码逻辑回归（本轮未改动调度算法代码）。

## 5. 仍需后续推进的风险

1. 专利候选（RS-P01~RS-P03）尚未做 claim-level 全文对照。
2. 当前技术效果证据以合成与消融为主，仍需真机基线对比补强。
3. 历史旧方向文档仍在仓库中，评审时必须明确“仅资源调度 v1 生效”。

## 6. 结论

本轮产出的 R13 文档链条可审计、可复核、与当前实现一致，可提交外部严格评审。  
下一轮应进入“专利全文级检索 + 真机对照实验 + 代理人收敛”阶段。
