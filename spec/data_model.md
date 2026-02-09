# 数据模型规范（v0.1）

更新时间：2026-02-09（UTC+08:00）

## 1. Fragment（记忆碎片）

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Fragment:
    fragment_id: str                 # 全局唯一 ID
    content: str                     # 原始文本内容
    source_agent: str                # 来源智能体
    timestamp: float                 # Unix 时间戳
    topic_candidates: List[str]      # 主题候选标签
    confidence: float                # 来源置信度 [0,1]
    tool_fingerprint: str            # 工具输出指纹
    citation_count: int              # 被后续步骤引用次数
    trace_pointer: str               # 外部原文 hash/ID
    embedding: List[float]           # 向量表示
    metadata: Dict[str, str]         # 扩展字段
```

约束：
- `fragment_id` 唯一，不可变。
- `confidence` 取值范围 `[0, 1]`。
- `trace_pointer` 必须可追溯到原始输入。

## 2. Cluster（语义簇）

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Cluster:
    cluster_id: str
    fragment_ids: List[str]
    centroid: List[float]
    topic_distribution: Dict[str, float]
    conflict_risk: float
    last_updated: float
```

约束：
- `fragment_ids` 至少包含 1 条碎片 ID。
- `topic_distribution` 概率和约为 1。
- `conflict_risk` 范围 `[0, 1]`。

## 3. ClusterMemoryUnit（簇记忆单元）

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ClusterMemoryUnit:
    cluster_id: str
    consensus_summary: str
    disagreements: List[Dict[str, str]]   # 争议点 A/B 与证据
    evidence_pointers: List[str]           # 可追溯证据 ID
    slot_coverage: Dict[str, float]        # 槽位覆盖率 [0,1]
    compression_report: Dict[str, str]     # 压缩/重试/修订记录
```

约束：
- `evidence_pointers` 不能为空。
- 若存在冲突，`disagreements` 至少包含 1 条记录。
- `slot_coverage` 中必须包含契约定义的必选槽位。

## 4. RetentionContract（偏好保留契约）

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class SlotConstraint:
    min_items: int
    min_coverage_ratio: float
    required: bool

@dataclass
class RetentionContract:
    contract_id: str
    version: str
    slots: Dict[str, SlotConstraint]
    source_weights: Dict[str, float]
    topic_allowlist: List[str]
    topic_blocklist: List[str]
    length_budget: int
    max_rounds: int
```

约束：
- `length_budget` > 0。
- `max_rounds` >= 1。
- `topic_allowlist` 与 `topic_blocklist` 不应交集。

## 5. 最小持久化表建议

| 表名 | 主键 | 关键字段 |
|---|---|---|
| `fragments` | `fragment_id` | `content, source_agent, confidence, trace_pointer, embedding` |
| `clusters` | `cluster_id` | `fragment_ids, centroid, conflict_risk` |
| `cluster_memory_units` | `cluster_id` | `consensus_summary, disagreements, evidence_pointers, slot_coverage` |
| `retention_contracts` | `contract_id` | `version, slots, source_weights, length_budget` |
| `audit_logs` | `event_id` | `cluster_id, action, status, timestamp` |
