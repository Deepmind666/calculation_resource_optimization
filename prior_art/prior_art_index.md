# Prior Art 索引（Step 2）

更新时间：2026-02-09（UTC+08:00）

## 说明
- 本清单用于专利避碰与权利要求差异化设计，不构成法律意见。
- 证据优先级：专利全文页面（Google Patents/Justia）> 论文原文（arXiv）> 官方框架文档。
- `风险等级` 含义：
  - `高`：与“聚类+摘要/共享记忆+压缩”核心叙事直接重叠。
  - `中`：提供实现路径或公共背景，可能压缩泛化叙事空间。
  - `低`：工程生态背景或间接相关。

## 清单（16 项）
| ID | 类型 | 名称 | 来源 | 核心关联点 | 风险等级 |
|---|---|---|---|---|---|
| PA-001 | 专利 | US10984781B2 Identifying representative conversations using a state model | https://patents.google.com/patent/US10984781B2/en | 会话状态序列、会话距离、聚类、代表会话/摘要 | 高 |
| PA-002 | 专利 | US11558334B2 Multi-message conversation summaries and annotations | https://patents.google.com/patent/US11558334 | 多消息会话可定制摘要、相似度与聚类、摘要注释链接 | 高 |
| PA-003 | 专利 | CN111639175B 一种自监督的对话文本摘要方法及系统 | https://patents.google.com/patent/CN111639175B/zh | 自监督分段 + 无监督主题聚类 + 生成式摘要 | 高 |
| PA-004 | 专利 | US12387050 Multi-stage LLM with unlimited context | https://patents.justia.com/patent/12387050 | 分层压缩、semantic clustering、共享 thought cache、多 agent 访问 | 高 |
| PA-005 | 论文 | MemGPT: Towards LLMs as Operating Systems (arXiv:2310.08560) | https://arxiv.org/abs/2310.08560 | 分层记忆与虚拟上下文管理 | 中 |
| PA-006 | 论文 | Generative Agents (arXiv:2304.03442) | https://arxiv.org/abs/2304.03442 | 记忆存储-反思-检索闭环 | 中 |
| PA-007 | 论文 | Memory Sharing for LLM Agents (arXiv:2404.09982) | https://arxiv.org/abs/2404.09982 | 多智能体共享记忆池与检索增强 | 中 |
| PA-008 | 论文 | TiMem (arXiv:2601.02845) | https://arxiv.org/abs/2601.02845 | 时间层级记忆树、记忆巩固与召回长度降低 | 中 |
| PA-009 | 论文 | HMT: Hierarchical Memory Transformer (arXiv:2405.06067) | https://arxiv.org/abs/2405.06067 | 层级记忆结构与长上下文建模 | 中 |
| PA-010 | 论文 | Infinite-LLM (arXiv:2401.02669) | https://arxiv.org/abs/2401.02669 | 长上下文服务系统与内存调度 | 中 |
| PA-011 | 论文 | Controllable Abstractive Summarization (arXiv:1711.05217) | https://arxiv.org/abs/1711.05217 | 用户可控摘要属性（长度/风格/实体关注） | 中 |
| PA-012 | 论文 | Controllable Abstractive Dialogue Summarization (arXiv:2105.14064) | https://arxiv.org/abs/2105.14064 | 对话摘要可控粒度与两阶段生成 | 中 |
| PA-013 | 框架文档 | LangGraph Memory overview | https://docs.langchain.com/oss/python/langgraph/memory | 线程短期记忆 + 跨线程长期记忆 | 中 |
| PA-014 | 框架文档 | LangGraph Persistence | https://docs.langchain.com/oss/python/langgraph/persistence | checkpointer、thread、checkpoint 状态持久化 | 中 |
| PA-015 | 框架文档 | LangChain Vector stores | https://docs.langchain.com/oss/python/integrations/vectorstores/ | 向量存储与相似检索统一接口 | 低 |
| PA-016 | 官方产品文档 | OpenAI Introducing Codex（含 AGENTS.md spec） | https://openai.com/index/introducing-codex/ | 仓库级 AGENTS.md 指令规范与代理执行约束 | 低 |

## 对本项目的直接约束结论
1. “碎片向量化-聚类-摘要”不能作为主创新叙事，会与 PA-001/002/003 直接冲突。
2. “多 agent 共享记忆 + 分层压缩 + 语义聚类”会被 PA-004/005/007/013/014 大幅覆盖。
3. 可行路线应转向组合差异：`偏好契约可执行化 + 证明式保真校验 + 全局预算分配优化 + 跨 agent 冗余仲裁`。
