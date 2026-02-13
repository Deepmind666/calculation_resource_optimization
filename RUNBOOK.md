# RUNBOOK

最后更新：2026-02-13

本手册用于快速、安全地执行本项目日常开发与验证。

---

## 1. 环境准备

最低建议：
1. Git 2.30+
2. Python 3.10+
3. PowerShell 5.1+
4. 可选：`psutil`（提升真实资源采样可观测性）

检查命令：

```powershell
git --version
python --version
```

---

## 2. 仓库初始化

```powershell
git clone https://github.com/Deepmind666/calculation_resource_optimization.git
cd calculation_resource_optimization
```

---

## 3. 验证三板斧（每次开发前后必跑）

说明：先清缓存，再进行结构、配置、测试三步验证。

```powershell
# Step 0: 清理缓存，避免旧 pyc 干扰
Get-ChildItem -Path prototype -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# Step 1: 结构检查
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1

# Step 2: 配置校验
python qa/validate_scheduler_config.py

# Step 3: 全量测试
python -m unittest discover -s prototype/tests -p "test_*.py"
```

判定规则：
1. 三板斧全部 PASS，方可进入“提交候选”状态。
2. 任一步失败，先修复再重跑，不允许跳步。

---

## 4. 常用运行命令

### 4.1 安全演示（dry-run）

```powershell
python prototype/main.py --ticks 12
```

### 4.2 基础实验

```powershell
python prototype/run_experiments.py
python prototype/run_patent_evidence.py
```

### 4.3 高级实验

```powershell
python prototype/run_advanced_research.py --trials 20
```

---

## 5. 真机事件驱动基线（完整命令）

说明：该命令用于触发并追踪“安全 + 吞吐”双目标事件链。

```powershell
python prototype/run_advanced_research.py \
  --trials 20 \
  --run-real-baseline \
  --real-target-eventful \
  --real-require-completion \
  --real-min-completed 1 \
  --real-max-attempts 4 \
  --real-task-count 6 \
  --real-task-duration-sec 2 \
  --real-base-mem-mb 96 \
  --real-fixed-workers 4 \
  --real-max-wall-sec 12
```

建议：
1. 先 dry-run 验证逻辑，再跑真机模式。
2. 保留运行输出与 `figures/` 产物用于评审复核。

---

## 6. 提交流程（安全规则）

### 6.1 检查改动

```powershell
git status --short
```

### 6.2 只按文件显式 add

```powershell
git add AGENTS.md RUNBOOK.md qa/review_checklist.md qa/codex_prompt_template.md
git add logs/work_progress.md .claude.md
```

禁止：
1. `git add .`
2. `git add -A`

### 6.3 提交与推送

```powershell
git commit -m "docs: update governance and review templates"
git push origin main
```

---

## 7. 每轮必须落盘的文件

1. `logs/work_progress.md`：时间戳 + 变更 + 清单 + 风险。
2. `qa/deep_algorithm_self_audit_R{N}_{date}.md`：8 章节自审计。
3. `.claude.md`：R{N} handoff note。

---

## 8. 常见故障与处理

1. 单测数量与自审计不一致：
   - 重新执行全量单测，以最终输出覆盖自审计。

2. 出现编码乱码：
   - 统一以 UTF-8 无 BOM 重新保存并复查。

3. ImportError 或行为与代码不一致：
   - 先清 `__pycache__`，再重跑三板斧。
