# 来源摘录与核验说明（Step 2 初稿）

更新时间：2026-02-09（UTC+08:00）

## 核验规则
- `已核验`：已查看原始页面并提炼要点。
- `待核验`：当前仅有标题/摘要层证据，后续需补充更细粒度摘录（建议在 R3 前完成）。

## 记录

### PA-001 US10984781B2（已核验）
- 来源：https://patents.google.com/patent/US10984781B2/en
- 摘要要点（转述）：
  - 以状态模型表征会话；
  - 基于会话间距离进行聚类；
  - 在簇内选择代表性会话/摘要信息。
- 对本项目影响：
  - “聚类后选代表摘要”叙事风险高，应避免作为独立权利要求核心。

### PA-002 US11558334B2（已核验）
- 来源：https://patents.google.com/patent/US11558334
- 摘要要点（转述）：
  - 多消息会话摘要可定制；
  - 支持摘要与注释/特征向量关联；
  - 涉及相似度比较与摘要生成流程。
- 对本项目影响：
  - “可控摘要”需从参数控制提升为“契约执行+校验”级别。

### PA-003 CN111639175B（已核验）
- 来源：https://patents.google.com/patent/CN111639175B/zh
- 摘要要点（转述）：
  - 语义向量表示；
  - 自监督分段；
  - 无监督主题聚类；
  - 编解码摘要生成。
- 对本项目影响：
  - 中文语境下“向量化+聚类+摘要”已有直接先例。

### PA-004 US12387050（已核验）
- 来源：https://patents.justia.com/patent/12387050
- 摘要要点（转述）：
  - 多阶段上下文压缩与扩展；
  - 明确提到语义聚类用于 consolidation；
  - shared cache 支持多 agent 访问。
- 对本项目影响：
  - 必须将创新写成工程可验证约束组合，而不是宏观系统叙事。

### PA-005 MemGPT（已核验）
- 来源：https://arxiv.org/abs/2310.08560
- 要点（转述）：
  - 将 LLM 上下文管理类比操作系统内存层级；
  - 通过外存与调度策略扩展可用上下文。

### PA-006 Generative Agents（已核验）
- 来源：https://arxiv.org/abs/2304.03442
- 要点（转述）：
  - 记忆-反思-规划闭环；
  - 长期记忆检索驱动行为生成。

### PA-007 Memory Sharing for LLM Agents（已核验）
- 来源：https://arxiv.org/abs/2404.09982
- 要点（转述）：
  - 多 agent 共享记忆机制；
  - 通过共享记忆提升协作任务表现。

### PA-008 TiMem（已核验）
- 来源：https://arxiv.org/abs/2601.02845
- 要点（转述）：
  - 时间层级记忆结构；
  - 通过层级压缩与检索降低上下文消耗。

### PA-009 HMT（已核验）
- 来源：https://arxiv.org/abs/2405.06067
- 要点（转述）：
  - 层级记忆 Transformer 支持长序列建模。

### PA-010 Infinite-LLM（已核验）
- 来源：https://arxiv.org/abs/2401.02669
- 要点（转述）：
  - 面向长上下文服务场景的架构方案。

### PA-011 Controllable Abstractive Summarization（已核验）
- 来源：https://arxiv.org/abs/1711.05217
- 要点（转述）：
  - 摘要可控属性（如长度、实体、风格）是已知研究方向。

### PA-012 Controllable Abstractive Dialogue Summarization（已核验）
- 来源：https://arxiv.org/abs/2105.14064
- 要点（转述）：
  - 对话摘要的可控生成策略与多阶段建模。

### PA-013 LangGraph Memory（已核验）
- 来源：https://docs.langchain.com/oss/python/langgraph/memory
- 要点（转述）：
  - 线程级短期记忆；
  - 跨线程长期记忆。

### PA-014 LangGraph Persistence（已核验）
- 来源：https://docs.langchain.com/oss/python/langgraph/persistence
- 要点（转述）：
  - checkpoint、thread、checkpoint_id 的持久化恢复机制。

### PA-015 LangChain Vector Stores（已核验）
- 来源：https://docs.langchain.com/oss/python/integrations/vectorstores/
- 要点（转述）：
  - 向量存储统一接口与检索集成能力。

### PA-016 OpenAI Introducing Codex（已核验）
- 来源：https://openai.com/index/introducing-codex/
- 要点（转述）：
  - AGENTS.md 可用于仓库级行为规范；
  - 支持可审计工作流。

## 待核验清单
1. 逐项补齐专利与论文的“关键段落行号/段落号”定位信息。
2. 对专利 PA-001/002/003/004 增加“权利要求独立项要点摘录”。
3. 对论文 PA-008/009/010 做年份、版本与最终发表状态核对。
