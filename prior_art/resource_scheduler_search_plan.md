# 资源调度 Prior Art 检索计划（R14）

- Timestamp: 2026-02-11 13:20:00 +08:00
- Owner: Codex (GPT-5)
- Scope: 计算资源动态调度与防爆保护（CPU/GPU/内存）
- 目标: 为“资源调度方向”建立可追溯先有技术证据链，支撑权利要求收敛与路线决策

## 1. 检索边界

1. 技术主题：
   - admission control（准入控制）
   - emergency/preemption（紧急回收/抢占）
   - per-GPU/device aware scheduling（设备级资源感知调度）
   - smoothing + hysteresis + cooldown（平滑 + 迟滞 + 冷却）
2. 业务边界：
   - 单机任务调度器（不限定容器平台）
   - 关注稳定性（防 OOM、避免资源爆炸）
3. 排除项：
   - 纯语义记忆、LLM 摘要、对话聚类等旧方向内容

## 2. 分类号与关键词策略

1. CPC 主类：
   - `G06F9/50`（任务调度）
   - `G06F11/34`（监控/故障管理）
2. 扩展关键词（英）：
   - `resource admission control`, `same tick cumulative projection`
   - `GPU affinity scheduling`, `device-aware admission`
   - `emergency preemption`, `node pressure eviction`
   - `EMA smoothing hysteresis scheduler`
3. 扩展关键词（中）：
   - 资源准入控制、同周期累计投影
   - GPU 亲和调度、设备感知准入
   - 紧急抢占回收、节点压力驱逐
   - EMA 平滑、迟滞冷却

## 3. 证据来源优先级

1. 官方系统文档（Kubernetes、Linux kernel、Slurm、Hadoop）
2. 一线调度系统论文（Borg、Omega）
3. 专利库（Google Patents 候选专利，后续需代理人二次检索确认）

## 4. 本轮已完成检索源（用于 R13）

1. Kubernetes:
   - Pod Priority and Preemption
   - Node-pressure Eviction
   - Resource Quotas
   - Dynamic Resource Allocation
   - Resource Bin Packing
2. Linux kernel:
   - PSI（Pressure Stall Information）
   - cgroup v2 memory controller（`memory.high`/`memory.max`）
3. HPC/Big Data:
   - Slurm preemption
   - YARN CapacityScheduler preemption
4. 论文:
   - Borg (EuroSys 2015)
   - Omega (EuroSys 2013)
5. 专利候选（已扩展）:
   - `US20200167197A1`
   - `US11656911B2`
   - `US20230385093A1`
   - `US20190155660A1`
   - `US10545796B2`
   - `CN114968601A`
   - `CN117788264A`
   - `WO2024032587A1`
   - `EP1163580B1`
6. CNIPA 检索入口：
   - `https://pss-system.cponline.cnipa.gov.cn/conventionalSearch`

## 5. 产出模板（统一）

每条 prior art 使用以下字段：
1. `来源`（URL）
2. `披露点`（可核验的技术事实）
3. `与本项目重叠点`
4. `与本项目差异点`
5. `风险级别`（高/中/低）
6. `状态`（已核验 / 待全文核验）

## 6. 验收标准

1. 至少 10 条资源调度方向可追溯来源
2. 每条都有“重叠 + 差异 + 风险”三段结论
3. 输出可直接用于权利要求收敛（非泛化描述）
4. 与代码实现存在映射关系（见 `qa/technique_claim_mapping_resource_scheduler_v1_2026-02-11.md`）

## 7. 风险与控制

1. 风险：仅凭工程文档容易高估新颖性
   - 控制：增加专利全文检索并由代理人复核
2. 风险：只看单一平台资料导致偏差
   - 控制：混合 K8s/Slurm/YARN/Linux/Borg/Omega 多源交叉
3. 风险：候选专利尚未做 claim-level 比对
   - 控制：在下一轮引入“权利要求逐条对照表”
