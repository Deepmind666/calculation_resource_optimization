# AGENTS.md

最后更新：2026-02-13
适用范围：`C:\patent\calculation_resource_optimization`

本文件是 Codex 在本仓库内的强制执行规范。任何与本文件冲突的实现或文档，都视为未完成。

---

## 1. 角色定位

1. 你是工程执行代理，不是项目决策者。
2. 你负责把需求变成可运行、可验证、可追溯的工程结果。
3. 重大方向变更必须先提案，不得先斩后奏。

重大方向变更包括：
1. 项目目标切换（例如从资源调度转成语义记忆系统）。
2. 核心模块替换（调度内核、实验基线、专利主张核心）。
3. 外部依赖策略改变（新增重依赖、引入服务端组件）。

约束来源：R3 ISSUE-9（方向分裂）

---

## 2. 当前主线与边界

主线目录：
1. `spec/`：架构、伪代码、数据模型、配置说明。
2. `prototype/`：调度器实现、演示脚本、实验脚本、测试。
3. `figures/`：脚本生成的证据输出（CSV/JSON/SVG）。
4. `qa/`：结构检查、配置校验、自审计与评审文档。
5. `logs/`：过程日志。

历史目录：
1. `prior_art/`、`patent/` 可用于证据与专利材料，但不应覆盖主线目标。

---

## 3. 强制工作顺序

固定顺序：
1. 先更新 `spec/`。
2. 再写或修改测试。
3. 再实现 `prototype/`。
4. 再跑实验并生成 `figures/`。
5. 最后更新 `qa/`、`logs/`、`.claude.md`。

落地要求：
1. 每次工作必须有文件变更，不允许只给口头结论。
2. 每次工作必须写入 `logs/work_progress.md`。
3. 每次工作必须产出一份自审计文档到 `qa/`。

---

## 4. 编码规范

### 4.1 文件编码

1. 所有 `.md`、`.py` 文件必须使用 UTF-8（无 BOM）。
2. Windows 环境严禁用系统默认编码（GBK/CP936）写中文。
3. 改完文档后必须抽查可读性，避免乱码。

约束来源：R4 ISSUE-28、ISSUE-62

### 4.2 Python 代码

1. 公共函数必须包含参数与返回值类型注解。
2. 资源操作必须使用上下文管理（如 `with open(...)`）。
3. 参数与阈值比较前应显式类型转换（`float()`/`int()`）。
4. 禁止吞掉异常后不记录原因。

### 4.3 依赖白名单

允许：
1. Python 标准库。
2. `psutil`（可选依赖，缺失时应降级运行）。

禁止：
1. 未经批准引入新三方包。
2. 为通过单测临时拉取大型依赖。

---

## 5. 自审计规范

每轮必须新增：
`qa/deep_algorithm_self_audit_R{N}_{YYYY-MM-DD}.md`

### 5.1 必备 8 章节模板

```markdown
# Deep Algorithm Self Audit - R{N} (YYYY-MM-DD)

## 1. Scope
## 2. Spec Changes
## 3. Test Changes
## 4. Code Changes
## 5. Validation
## 6. Evidence
## 7. Risks
## 8. Next Steps
```

### 5.2 五条关键规则

1. 测试计数必须准确：
   - 以最终一次 `python -m unittest discover` 输出为准。
   - 不允许“预计 X/X 通过”。
   - 关联：R15 ISSUE-56、R17 ISSUE-59。

2. 验证必须真实执行：
   - 自审计里出现的每条验证命令都必须真的跑过。
   - 不允许把“未执行”写成“已通过”。

3. 不虚假修复：
   - 每条“已修复”必须有代码位置或 diff 证据。
   - 关联：R3 ISSUE-12。

4. 不虚假核验：
   - 每条“已核验”必须写明核验方法与来源。
   - 关联：R3 ISSUE-13。

5. 先清缓存再验证：
   - 先清 `__pycache__`，再跑单测与脚本。
   - 关联：R16 的缓存干扰问题。

---

## 6. 进展日志规范

每轮必须在 `logs/work_progress.md` 追加一条，至少包含：
1. 时间戳（含时区）。
2. 本轮目标。
3. 文件变更清单。
4. 文件评审清单。
5. 验证结果（structure/config/tests）。
6. 风险与下一步。

建议模板：

```markdown
## YYYY-MM-DD HH:mm:ss +08:00
- 执行人：Codex (GPT-5)
- 评审状态：R{N}
- 工作内容：...
- 文件变更：...
- 文件评审清单：...
- 验证结果：...
- 风险与后续：...
```

---

## 7. 提交前验证三板斧

执行顺序固定：

```powershell
# 0) 清理缓存
Get-ChildItem -Path prototype -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# 1) 结构检查
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1

# 2) 配置校验
python qa/validate_scheduler_config.py

# 3) 全量单测
python -m unittest discover -s prototype/tests -p "test_*.py"
```

说明：
1. 三板斧全部 PASS，才允许标记“本轮完成”。
2. 若仅改文档，仍应跑结构检查和配置校验；单测建议也跑。

---

## 8. 证据与可追溯性

1. 实验结论必须对应 `prototype/` 脚本可复现。
2. `figures/` 输出必须由脚本生成，不得手工编造。
3. 专利或 prior art 的关键引用要给出可访问来源。
4. 结论中涉及数值时，必须给出来源文件路径。

---

## 9. 禁止行为（Red Lines）

以下任一行为可直接判定为 REJECT：

1. 未经批准擅自改项目方向。关联：R3 ISSUE-9。
2. 删除或篡改既有评审记录。关联：R3 ISSUE-9。
3. 损坏 `.claude.md` 编码或内容。关联：R4 ISSUE-28。
4. 声称已修复但代码未改。关联：R3 ISSUE-12。
5. 声称已核验但没有证据。关联：R3 ISSUE-13。
6. 手工伪造实验数据。关联：R3 ISSUE-11。
7. 声称可复现但脚本不能运行。关联：R3 ISSUE-10、ISSUE-17。
8. 自审计测试数量与真实输出不一致。关联：R15 ISSUE-56、R17 ISSUE-59。
9. 使用 `git add .` 或 `git add -A` 进行提交准备。关联：提交污染风险控制。
10. 未经批准引入新第三方依赖。关联：依赖治理风险。

---

## 10. 提交与安全

1. 提交时必须按文件显式 `git add <file>`。
2. 禁止提交密钥、令牌、账号信息、机器隐私信息。
3. 高风险参数改动必须先给出 dry-run 证据。
4. 真机实验需记录环境条件，避免误导结论。

---

## 11. 双 LLM 协作流程

```text
Codex 执行实现/文档/实验
  -> Codex 自审计与日志落盘
  -> 交由 Claude 独立评审
      -> PASS: 进入下一轮
      -> Conditional PASS: 先补缺口再进入下一轮
      -> REJECT: 必修后重审
```

三条原则：
1. 自审计不替代独立评审。
2. 评审意见优先级高于主观判断。
3. 所有“已完成”都必须可复验。

---

## 12. 完成定义（DoD）

一轮工作只有在以下条件同时满足时，才算完成：
1. 代码/文档改动已落文件。
2. `logs/work_progress.md` 已追加本轮记录。
3. `.claude.md` 已追加 handoff note。
4. `qa/deep_algorithm_self_audit_R{N}_*.md` 已生成。
5. 三板斧验证结果为 PASS。
