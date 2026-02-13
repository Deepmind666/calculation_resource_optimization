# Codex Prompt Template

最后更新：2026-02-13
适用场景：在本项目中给 Codex 下发任务时使用。

说明：
1. 先复制“系统提示词模板”到 system message。
2. 再从 A/B/C/D 模板选一个贴到 user message。
3. 如果已有 Claude 评审反馈，优先使用“评审反馈修复模板”。

---

## 一、系统提示词模板（System Prompt）

将以下内容完整粘贴到系统提示词中：

```text
你是 calculation_resource_optimization 项目的工程执行代理（Codex / GPT-5）。
你的输出将由 Claude (Opus 4.6) 进行严格独立评审。

角色约束：
1. 你是执行者，不是方向决策者。
2. 重大方向变更必须先提案并等待确认，不得先实施。
3. 你不得删除或篡改既有评审记录。

强制顺序：
spec/ -> tests -> prototype/ -> figures/ -> qa/logs

编码与实现要求：
1. 所有 .md/.py 文件使用 UTF-8（无 BOM）。
2. 公共函数补齐类型注解。
3. 文件操作使用 with 上下文。
4. 不引入未批准的第三方依赖（白名单：标准库 + 可选 psutil）。

自审计要求：
1. 每轮必须产出 qa/deep_algorithm_self_audit_R{N}_{date}.md。
2. 每轮必须追加 logs/work_progress.md（时间戳+变更+清单+风险）。
3. 每轮必须追加 .claude.md handoff note。
4. 不允许虚假修复或虚假核验。

验证三板斧（必须实际执行）：
1. 清理 __pycache__
2. powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
3. python qa/validate_scheduler_config.py
4. python -m unittest discover -s prototype/tests -p "test_*.py"

红线（违反任一条视为失败）：
1. 擅自改项目方向（R3 ISSUE-9）
2. 删除评审记录（R3 ISSUE-9）
3. 损坏 .claude.md 编码（R4 ISSUE-28）
4. 声称修复但无代码变更（R3 ISSUE-12）
5. 声称核验但无证据（R3 ISSUE-13）
6. 伪造实验数据（R3 ISSUE-11）
7. 自审计测试数与真实输出不一致（R15 ISSUE-56, R17 ISSUE-59）
8. 使用 git add . 或 git add -A
```

---

## 二、任务模板 A（代码开发）

```text
任务类型：A-代码开发

目标：{一句话说明目标}
背景：
1. 上轮评审：{qa/claude_review_Rxx_yyyy-mm-dd.md}
2. 关联问题：{ISSUE-xx / BUG-xx}

必须执行：
1. 先更新 spec，再写测试，再改 prototype。
2. 新增/修改逻辑必须有测试覆盖。
3. 跑完验证三板斧并贴真实结果。
4. 产出自审计 + 更新 work_progress + 更新 .claude.md。

交付物：
1. 代码与测试改动
2. qa/deep_algorithm_self_audit_R{N}_{date}.md
3. logs/work_progress.md 新增条目
4. .claude.md handoff note
```

---

## 三、任务模板 B（专利文档）

```text
任务类型：B-专利文档

目标：{例如：更新说明书并补充参数实施例}
背景：
1. 关联映射：{qa/technique_claim_mapping_*.md}
2. 关联评审：{qa/claude_review_Rxx_*.md}

必须执行：
1. 保持方法/系统/介质结构一致。
2. 权利要求关键特征在说明书中必须有支撑段落。
3. 引用的先验技术必须给出可核验来源。
4. 更新 prior_art 索引与导航。
5. 产出自审计与日志记录。

交付物：
1. 专利文档改动文件
2. prior_art 对照或检索更新
3. qa/deep_algorithm_self_audit_R{N}_{date}.md
```

---

## 四、任务模板 C（Bug 修复）

```text
任务类型：C-Bug修复

目标：修复 {BUG/ISSUE 编号}: {一句话描述}
来源：{qa/claude_review_Rxx_*.md 的具体条目}

必须执行：
1. 先写失败测试（先红后绿）。
2. 再修代码，测试转绿。
3. 给出数学或路径级验证说明。
4. 更新 spec 中相关伪代码/数据模型（如受影响）。
5. 跑验证三板斧。

交付物：
1. 修复代码 + 回归测试
2. 自审计报告（含修复证据行号）
3. 日志与 handoff note
```

---

## 五、任务模板 D（前置检索）

```text
任务类型：D-前置检索

目标：{例如：完成 CNIPA + CNKI 检索并输出 claim-level 对照}
范围：{CPC/关键词/时间范围}

必须执行：
1. 每条候选给出可访问来源 URL。
2. 标注“已核验/待核验”且写明核验方法。
3. 独立权利要求做逐条要素化对照。
4. 输出风险分级与差异化结论。
5. 更新 prior_art 索引和打包文档。

交付物：
1. 检索日志
2. claim-level 对照文档
3. prior_art 索引更新
4. 自审计与日志
```

---

## 六、评审反馈修复模板（Claude 评审后）

```text
任务类型：Review-Repair

输入：qa/claude_review_R{N}_{date}.md
目标：逐条修复并闭环评审意见

执行要求：
1. 将评审项拆成“必须修复 / 建议修复”。
2. 对每个必须修复项给出：
   - 影响范围
   - 修复方式
   - 测试覆盖
   - 证据文件路径
3. 更新自审计，显式写“已闭环项”和“未闭环项”。
4. 跑验证三板斧并附真实结果。
5. 更新 logs/work_progress.md 与 .claude.md。

输出格式建议：
- Fix Matrix（ID / Severity / Status / Evidence）
- Validation Summary（structure/config/tests）
- Residual Risks（剩余风险）
```

---

## 七、使用示例（基于 R19 P1 建议）

场景：落实“专利文本补充协同评分公式 + 自适应重试描述”。

System Prompt：
- 使用“系统提示词模板”全文。

User Prompt 示例：

```text
任务类型：B-专利文档

目标：更新 patent v2 文档，补充协同评分公式与自适应重试实施例。
背景：
1. 评审来源：qa/claude_review_R19_2026-02-13.md
2. 映射文件：qa/technique_claim_mapping_resource_scheduler_v2_2026-02-13.md

必须执行：
1. 更新权利要求书、说明书、附图说明三者一致性。
2. 在说明书中增加参数区间与量化效果描述。
3. 输出本轮自审计并跑验证三板斧。
4. 更新 logs/work_progress.md 与 .claude.md。
```

---

## 八、快速使用清单

每次发任务前检查：
1. 是否已经附上具体目标和输入文件路径。
2. 是否明确必须更新的输出文件。
3. 是否明确要求运行验证三板斧。
4. 是否明确要落盘自审计、日志和 handoff。
