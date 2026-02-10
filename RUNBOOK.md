# RUNBOOK

## 1. 环境检查
```powershell
git --version
python --version
```

建议：
1. Python 3.10+
2. PowerShell 5.1+
3. 可选：安装 `psutil` 以获得更稳定的 CPU/内存采样

## 2. 克隆仓库
```powershell
git clone https://github.com/Deepmind666/calculation_resource_optimization.git
cd calculation_resource_optimization
```

## 3. 自查
```powershell
powershell -ExecutionPolicy Bypass -File qa/structure_check.ps1
python qa/validate_scheduler_config.py spec/scheduler_config.example.json
```

## 4. 运行原型（安全 dry-run）
```powershell
cd prototype
python main.py --ticks 12
python run_experiments.py
python -m unittest discover -s tests -p "test_*.py"
cd ..
```

## 5. 可选：真实子进程模式
```powershell
cd prototype
python main.py --real-run --ticks 12
cd ..
```

## 6. 提交与推送（安全模式）
```powershell
git status --short
git add AGENTS.md .claude.md .gitignore README.md RUNBOOK.md gptdeepsearch2_9.md logs prior_art spec prototype patent figures qa
git commit -m "chore: update scheduler project artifacts"
git push origin main
```

## 7. 工作规则
1. 每次工作都更新 `logs/work_progress.md`（时间戳 + 清单 + 风险）。
2. 每次提交前至少跑一次自查和单测。
