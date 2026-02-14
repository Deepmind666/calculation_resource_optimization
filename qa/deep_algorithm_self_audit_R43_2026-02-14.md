# Deep Algorithm Self Audit - R43 (2026-02-14)

## 1. Scope
1. `spec/cnipa_formal_document_profile_R43.md`
2. `patent/README.md`
3. `logs/work_progress.md`
4. `.claude.md`

## 2. Spec Changes
1. 新增 `spec/cnipa_formal_document_profile_R43.md`。
2. 约定 CNIPA 风格申请文稿的结构、措辞规则和附图文本规则。

## 3. Test Changes
1. 本轮未新增或修改测试代码。
2. 已执行全量单测并记录真实输出。

## 4. Code Changes
1. 本轮未修改 `prototype/` 运行代码。
2. 新增文档：
   - `patent/权利要求书_资源调度_CNIPA_格式化稿_R43.md`
   - `patent/说明书_资源调度_CNIPA_格式化稿_R43.md`
   - `patent/附图文字描述稿_CNIPA_R43.md`
   - `patent/附图标记说明表_资源调度_CNIPA_R43.md`
3. 更新文档：
   - `patent/README.md`
   - `logs/work_progress.md`
   - `.claude.md`

## 5. Validation
1. 清缓存（先于验证执行）：
   - `cmd /c "if exist prototype\__pycache__ rd /s /q prototype\__pycache__ & if exist prototype\tests\__pycache__ rd /s /q prototype\tests\__pycache__"` -> PASS
2. 结构检查：
   - `powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1` -> PASS
3. 配置校验：
   - `python qa/validate_scheduler_config.py` -> PASS
4. 全量单测：
   - `python -m unittest discover -s prototype/tests -p "test_*.py"` -> PASS
   - `Ran 75 tests in 0.488s`

## 6. Evidence
1. 已产出 CNIPA 风格格式稿（权利要求书、说明书）。
2. 已产出附图文字描述稿，包含“正式附图说明句”与“绘图文字描述”。
3. 已产出资源调度方向的附图标记说明表，避免使用旧方向标记。
4. 编码检查（UTF-8 无 BOM）：
   - `spec/cnipa_formal_document_profile_R43.md`
   - `patent/权利要求书_资源调度_CNIPA_格式化稿_R43.md`
   - `patent/说明书_资源调度_CNIPA_格式化稿_R43.md`
   - `patent/附图文字描述稿_CNIPA_R43.md`
   - `patent/附图标记说明表_资源调度_CNIPA_R43.md`
   - `qa/deep_algorithm_self_audit_R43_2026-02-14.md`

## 7. Risks
1. 当前为工程格式化稿，正式法律口径仍需代理人终稿化。
2. 旧文件 `patent/附图标记表.md` 仍在仓库中，评审时应优先使用 R43 新表。
3. 若代理人调整附图编号，需同步更新权利要求与说明书引用。

## 8. Next Steps
1. 生成 CNIPA 提交包目录（权利要求书/说明书/摘要/附图说明/附图）。
2. 产出“附图审校清单”（编号一致性、术语一致性、箭头方向一致性）。
3. 与代理人确认最终编号体系后冻结提交版本。
