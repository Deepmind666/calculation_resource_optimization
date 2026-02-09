# RUNBOOK

## 1. 环境准备
```powershell
git --version
python --version
```

建议环境：
- Windows PowerShell 5.1+ 或 PowerShell 7+
- Python 3.10+

## 2. 仓库准备（首次克隆）
```powershell
git clone https://github.com/Deepmind666/calculation_resource_optimization.git
cd calculation_resource_optimization
```

## 3. 远程绑定（已有本地目录时）
```powershell
git init
git branch -M main
git remote remove origin 2>$null
git remote add origin https://github.com/Deepmind666/calculation_resource_optimization.git
git remote -v
```

## 4. 结构自查
```powershell
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
```

## 5. 查看最新进展日志
```powershell
Get-Content -Tail 120 logs/work_progress.md
```

## 6. 提交与推送（安全模式）
```powershell
git status --short
git add AGENTS.md .claude.md .gitignore README.md RUNBOOK.md gptdeepsearch2_9.md logs prior_art spec prototype patent figures qa
git commit -m "chore: update project artifacts"
git push origin main
```

## 7. 工作要求
1. 每次改动后更新 `logs/work_progress.md`。
2. 每次提交前执行 `qa/structure_check.ps1`。
3. 新增流程或命令时，同步更新 `RUNBOOK.md` 与 `.claude.md`。
