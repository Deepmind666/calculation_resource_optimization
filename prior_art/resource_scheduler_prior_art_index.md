# 资源调度 Prior Art 索引（R14 修订）

- Timestamp: 2026-02-11 13:20:00 +08:00
- Owner: Codex (GPT-5)
- 修订目标: 响应 R12 评审 ISSUE-45/46/47

## 1. 公开资料与论文（已核验）

| ID | 来源 | 主要披露点 | 与本项目重叠点 | 与本项目差异点 | 风险 |
|---|---|---|---|---|---|
| RS-001 | Kubernetes Pod Priority and Preemption https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/ | 高优先级触发低优任务抢占 | 有优先级抢占 | 无 per-GPU 同 tick 分桶累计投影 | 中 |
| RS-002 | Kubernetes Node-pressure Eviction https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/ | 节点压力阈值驱逐 | 有紧急阈值回收思想 | 偏节点级，不是任务级 admission + preemption 闭环 | 中 |
| RS-003 | Kubernetes ResourceQuota https://kubernetes.io/docs/concepts/policy/resource-quotas/ | 资源总量上限 | 有准入约束思想 | 非同 tick 累计投影 | 中 |
| RS-004 | Kubernetes Dynamic Resource Allocation https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/ | 动态设备资源分配 | 有设备资源管理 | 无 target-GPU 投影与保守 unbound 分治 | 中 |
| RS-005 | Kubernetes Resource Bin Packing https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/ | 多资源调度打分 | 有多资源评分思想 | 目标是放置优化，不是防爆回收闭环 | 中 |
| RS-006 | Slurm Preemption https://slurm.schedmd.com/preempt.html | 可配置抢占策略 | 有抢占机制 | 无 raw+EMA 双视图与 GPU 热点定向回收 | 中 |
| RS-007 | YARN CapacityScheduler https://hadoop.apache.org/docs/current/hadoop-yarn/hadoop-yarn-site/CapacityScheduler.html | 队列容量与预留/抢占 | 有资源压力回收 | 不是单机多维防爆调度 | 中 |
| RS-008 | Linux PSI https://docs.kernel.org/accounting/psi.html | CPU/内存/IO 压力观测 | 监控压力可用于模式切换 | 仅观测接口，无 admission/preemption 策略 | 低 |
| RS-009 | Linux cgroup v2 https://docs.kernel.org/admin-guide/cgroup-v2.html | `memory.high`/`memory.max` 控制 | 防爆目标相关 | 内核层硬限制，不含任务优先级与亲和判定 | 低 |
| RS-010 | Borg (EuroSys 2015) https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/ | 大规模调度、优先级与隔离 | 调度治理基础 | 未披露本项目三点组合 | 中 |
| RS-011 | Omega (EuroSys 2013) https://research.google/pubs/pub41684 | 共享状态并发调度 | 调度架构相关 | 关注并发架构，非本项目防爆机制 | 低 |
| RS-012 | Sparrow (SOSP 2013) https://amplab.cs.berkeley.edu/publication/sparrow-distributed-low-latency-scheduling/ | 低延迟分布式调度 | 调度策略背景 | 非资源防爆 admission/preemption | 低 |
| RS-013 | Apollo (OSDI 2014) https://www.microsoft.com/en-us/research/publication/apollo-scalable-and-coordinated-scheduling-for-cloud-scale-computing-2/ | 云规模协调调度 | 资源调度背景 | 非 per-GPU 显存准入与定向回收 | 低 |
| RS-014 | Medea (EuroSys 2018) https://www.microsoft.com/en-us/research/publication/medea-scheduling-long-running-applications-shared-production-clusters/ | 长短任务混部调度 | 多约束调度背景 | 非同 tick 累计预算与紧急双目标回收 | 低 |
| RS-015 | Firmament (OSDI 2016) https://research.google/pubs/firmament-fast-centralized-cluster-scheduling-at-scale/ | 中央化高质量放置调度 | 调度优化背景 | 非紧急防爆闭环 | 低 |
| RS-016 | Affinity-aware provisioning (arXiv 2022) https://arxiv.org/abs/2208.12738 | 亲和性资源供给 | 亲和性思想相关 | 场景是长期应用部署，不是瞬时防爆 | 低 |

## 2. 专利候选（已扩展到 9 条）

| ID | 来源 | 关键信息 | 与本项目重叠 | 风险 | 状态 |
|---|---|---|---|---|---|
| RS-P01 | US20200167197A1 https://patents.google.com/patent/US20200167197A1/en | 标题即“preemptive termination... free resources for high priority items”；Claim 1 含资源发现、pending 发现、策略引擎、终止与重调度 | 与 CP-2（资源感知抢占）高度重叠 | **高** | 已核验（需 claim-level 深比对） |
| RS-P01-G | US11656911B2 https://patents.google.com/patent/US11656911B2/en | RS-P01 授权版本（同族） | 与 CP-2 高重叠 | **高** | 已核验 |
| RS-P02 | US20230385093A1 https://patents.google.com/patent/US20230385093A1/en | GPU 虚拟化环境自适应 timeslice 调度，含 round-robin 与 preemption overhead 调整 | 与 GPU 调度相关，但目标是计算时间片，不是显存准入投影 | 中 | 已核验 |
| RS-P03 | US20190155660A1 https://patents.google.com/patent/US20190155660A1/en | 异构硬件计算调度系统 | 与异构资源调度背景重叠 | 中 | 标题级核验 |
| RS-P04 | CN114968601A https://patents.google.com/patent/CN114968601A/zh | AI 训练作业按比例预留资源调度 | 与资源预留/调度重叠 | 中 | 标题级核验 |
| RS-P05 | CN117788264A https://patents.google.com/patent/CN117788264A/en | GPU 虚拟化与任务调度，含显存需求和规则分配 | 与 GPU 资源分配相关 | 中 | 已核验 |
| RS-P06 | WO2024032587A1 https://patents.google.com/patent/WO2024032587A1/en | GPU 资源使用与虚拟化、作业调度 | 与 GPU 调度背景重叠 | 中 | 标题级核验 |
| RS-P07 | EP1163580B1 https://patents.google.com/patent/EP1163580B1/en | 早期资源调度类专利 | 通用调度背景 | 低 | 标题级核验 |
| RS-P08 | US10545796B2 https://patents.google.com/patent/US10545796B2/en | RS-P01 家族早期授权文献 | 与 CP-2 高重叠 | **高** | 标题级核验 |

注：
1. RS-P01 家族（A1/B2）已升级为高风险，后续必须做 claim-level 对照。

## 3. CNIPA 检索路径与记录（补齐 ISSUE-47）

1. CNIPA 官方介绍页（系统说明）：
   - https://www.cnipa.gov.cn/art/2023/2/13/art_3166_182074.html
2. CNIPA 官方检索入口（公众检索）：
   - https://pss-system.cponline.cnipa.gov.cn/conventionalSearch
3. CNIPA 公共服务指引（含入口说明）：
   - https://www.cnipa.gov.cn/art/2024/4/1/art_3359_191346.html

本轮已将 CNIPA 检索路径纳入正式索引，并将下一轮检索任务细化为：
1. 按 `G06F9/50`、`G06F11/34` 在 CNIPA 做检索与结果导出；
2. 对 RS-P01 家族和 CN 方向候选做 claim-level 逐条对比；
3. 输出可提交代理人的“相似权利要求对照表”。

## 4. 当前结论（修订）

1. ISSUE-45：已修正。RS-P01 风险从“中”上调为“高”。
2. ISSUE-46：已修正。RS-P02 已改为“GPU 虚拟化 timeslice 调度”描述。
3. ISSUE-47：已补强。新增 CNIPA 官方检索路径 + 专利候选扩展到 9 条。
4. 仍待下一轮：claim-level 全文比对与中国学术论文（CNKI/万方）深检索。
