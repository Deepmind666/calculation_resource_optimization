# Deep Algorithm Self Audit - R46 (2026-02-14)

## 1. Scope

本轮聚焦文档修复，不改 `prototype/` 代码与测试逻辑。

目标：
1. 修复 `patent/说明书_资源调度_CNIPA_完整稿_R44.md` 的拼接结构错误，改为单文档 CNIPA 六章结构。
2. 充实 `patent/权利要求书_资源调度_CNIPA_修正版_R44.md` 的从属权利要求 5/6/7，使其具有可执行技术特征。
3. 在附图文字稿中增加“实验阶段图面、提交前需中文化与编号一致性复核”的正式说明。

## 2. Spec Changes

1. 新增修复规范：`spec/cnipa_single_document_fix_profile_R46.md`。
2. 明确内容映射规则：
   - `v3 §2.1 + §2.2 + §2.3` -> 背景技术。
   - `v3 §3.1 + §3.2 + §3.3` -> 发明内容。
   - `v3 §5~§20` -> 具体实施方式。
3. 明确权利要求 5/6/7 补强规则与附图规范化声明要求。

## 3. Test Changes

本轮未新增或修改测试文件。

## 4. Code Changes

本轮为专利文档修复，未修改 `prototype/` 代码。

文档变更：
1. `patent/说明书_资源调度_CNIPA_完整稿_R44.md`
   - 修复为单文档六章结构（无二次拼接）。
   - 新增 `5.2 图面规范化说明`。
   - 在具体实施方式中补强阻断审计、终止失败保护、自适应调优参数细节。
2. `patent/权利要求书_资源调度_CNIPA_修正版_R44.md`
   - 充实权利要求 5/6/7。
3. `patent/附图文字描述稿_CNIPA_R43.md`
   - 新增“图面状态说明（提交前必看）”。

## 5. Validation

执行时间：2026-02-14（本地）

1. 清理缓存：
   - `cmd /c rmdir /s /q "C:\patent\calculation_resource_optimization\prototype\__pycache__"`
   - `cmd /c rmdir /s /q "C:\patent\calculation_resource_optimization\prototype\tests\__pycache__"`
   - 复核：`Get-ChildItem -Path prototype -Recurse -Directory -Filter '__pycache__'` 输出为空。

2. 结构检查：
   - 命令：`powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1`
   - 结果：PASS。

3. 配置校验：
   - 命令：`python qa/validate_scheduler_config.py`
   - 结果：PASS。

4. 全量单测：
   - 命令：`python -m unittest discover -s prototype/tests -p "test_*.py"`
   - 结果：`Ran 75 tests in 0.481s`，`OK`。

5. 文档结构自检：
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md` 顶层仅保留六章：
     - 一、发明名称
     - 二、技术领域
     - 三、背景技术
     - 四、发明内容
     - 五、附图说明
     - 六、具体实施方式
   - 行数：684 行（满足充分公开长度要求，不是缩水稿）。

## 6. Evidence

1. 单文档六章结构与关键段：
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:3`
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:18`
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:129`
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:203`

2. 附图规范化声明：
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:194`
   - `patent/附图文字描述稿_CNIPA_R43.md:6`

3. 权利要求 5/6/7 充实：
   - `patent/权利要求书_资源调度_CNIPA_修正版_R44.md:16`
   - `patent/权利要求书_资源调度_CNIPA_修正版_R44.md:18`
   - `patent/权利要求书_资源调度_CNIPA_修正版_R44.md:20`

4. 说明书对 5/6/7 的支撑段：
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:328`
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:330`
   - `patent/说明书_资源调度_CNIPA_完整稿_R44.md:343`

## 7. Risks

1. 当前 SVG 仍为实验阶段图面，尚未完成正式提交版中文标注与编号统一。
2. 本轮未重绘附图，仅完成“提交前规范化要求”落文与可审查提醒。

## 8. Next Steps

1. 基于 `patent/附图文字描述稿_CNIPA_R43.md` 统一重绘图1~图4，完成中文化与参考编号闭环。
2. 用同一编号体系复核 `附图标记说明表`、说明书正文和权利要求文本。
3. 形成师兄评审包：R44 修正说明书 + 修正权利要求 + 附图规范化计划单。
