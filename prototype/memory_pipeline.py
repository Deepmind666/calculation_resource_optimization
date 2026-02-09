from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import re
import time
from typing import Dict, List, Tuple


EMBED_DIM = 64


@dataclass(frozen=True)
class Fragment:
    fragment_id: str
    content: str
    source_agent: str
    timestamp: float
    trace_pointer: str
    confidence: float
    topic_candidates: List[str]
    embedding: List[float]


@dataclass
class Cluster:
    cluster_id: str
    fragment_ids: List[str] = field(default_factory=list)
    centroid: List[float] = field(default_factory=lambda: [0.0] * EMBED_DIM)
    topic_distribution: Dict[str, float] = field(default_factory=dict)
    conflict_risk: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class SlotConstraint:
    required: bool
    min_coverage_ratio: float
    min_items: int
    note: str = ""


@dataclass
class RetentionContract:
    contract_id: str
    version: str
    domain: str
    required_slots: List[str]
    slot_constraints: Dict[str, SlotConstraint]
    source_weights: Dict[str, float]
    topic_allowlist: List[str]
    topic_blocklist: List[str]
    global_token_budget: int
    per_cluster_min_tokens: int
    per_cluster_max_tokens: int
    max_rewrite_rounds: int
    require_entailment_check: bool
    require_conflict_check: bool


def tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[\s,，。；;:：()（）\[\]{}]+", text.lower()) if t]


def embed_text(text: str, dim: int = EMBED_DIM) -> List[float]:
    vec = [0.0] * dim
    for tok in tokenize(text):
        h = hashlib.sha256(tok.encode("utf-8")).hexdigest()
        idx = int(h[:8], 16) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vector size mismatch.")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def update_topic_distribution(dist: Dict[str, float], topics: List[str]) -> Dict[str, float]:
    updated = dict(dist)
    for t in topics:
        updated[t] = updated.get(t, 0.0) + 1.0
    total = sum(updated.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in updated.items()}


def ingest_fragment(
    fragment_id: str,
    content: str,
    source_agent: str,
    trace_pointer: str,
    confidence: float = 1.0,
    topics: List[str] | None = None,
) -> Fragment:
    if topics is None:
        topics = []
    return Fragment(
        fragment_id=fragment_id,
        content=content.strip(),
        source_agent=source_agent,
        timestamp=time.time(),
        trace_pointer=trace_pointer,
        confidence=max(0.0, min(1.0, confidence)),
        topic_candidates=topics,
        embedding=embed_text(content),
    )


def assign_or_create_cluster(
    fragment: Fragment,
    clusters: Dict[str, Cluster],
    similarity_threshold: float = 0.45,
) -> str:
    best_id = ""
    best_score = -1.0
    for cid, c in clusters.items():
        score = cosine(fragment.embedding, c.centroid)
        if score > best_score:
            best_id = cid
            best_score = score

    if best_score < similarity_threshold or not best_id:
        new_id = f"C-{len(clusters) + 1:04d}"
        clusters[new_id] = Cluster(
            cluster_id=new_id,
            fragment_ids=[fragment.fragment_id],
            centroid=list(fragment.embedding),
            topic_distribution=update_topic_distribution({}, fragment.topic_candidates),
            last_updated=time.time(),
        )
        return new_id

    cluster = clusters[best_id]
    cluster.fragment_ids.append(fragment.fragment_id)
    n = len(cluster.fragment_ids)
    cluster.centroid = [
        ((n - 1) * old + new) / n for old, new in zip(cluster.centroid, fragment.embedding)
    ]
    cluster.topic_distribution = update_topic_distribution(
        cluster.topic_distribution, fragment.topic_candidates
    )
    cluster.last_updated = time.time()
    return best_id


def extract_key_values(text: str) -> Dict[str, str]:
    pairs = {}
    pattern = re.compile(r"([A-Za-z0-9_\u4e00-\u9fff-]+)\s*[:=：]\s*([A-Za-z0-9_\u4e00-\u9fff.%+-]+)")
    for k, v in pattern.findall(text):
        pairs[k.strip().lower()] = v.strip()
    return pairs


def detect_conflicts(fragments: List[Fragment]) -> List[Dict[str, str]]:
    key_to_values: Dict[str, Dict[str, List[str]]] = {}
    for f in fragments:
        kv = extract_key_values(f.content)
        for key, value in kv.items():
            if key not in key_to_values:
                key_to_values[key] = {}
            key_to_values[key].setdefault(value, []).append(f.fragment_id)

    conflicts = []
    for key, values in key_to_values.items():
        if len(values) > 1:
            sorted_values = sorted(values.items(), key=lambda x: x[0])
            a_value, a_ids = sorted_values[0]
            b_value, b_ids = sorted_values[1]
            conflicts.append(
                {
                    "key": key,
                    "A": f"{key}={a_value}",
                    "B": f"{key}={b_value}",
                    "evidence": ",".join(a_ids + b_ids),
                }
            )
    return conflicts


def build_slot_content(
    fragments: List[Fragment],
    conflicts: List[Dict[str, str]],
    contract: RetentionContract,
) -> Dict[str, List[str]]:
    slot_content: Dict[str, List[str]] = {slot: [] for slot in contract.required_slots}
    for f in fragments:
        text = f.content
        if "facts" in slot_content:
            slot_content["facts"].append(text)
        if "procedure-steps" in slot_content and ("步骤" in text or "step" in text.lower()):
            slot_content["procedure-steps"].append(text)
        if "rationale" in slot_content and ("因为" in text or "原因" in text):
            slot_content["rationale"].append(text)
        if "decisions" in slot_content and any(x in text for x in ["决定", "采用", "选择"]):
            slot_content["decisions"].append(text)
        if "parameter-ranges" in slot_content:
            kv = extract_key_values(text)
            for k, v in kv.items():
                slot_content["parameter-ranges"].append(f"{k}={v}")
        if "tool-results" in slot_content and any(x in text.lower() for x in ["result", "output", "pass", "失败"]):
            slot_content["tool-results"].append(text)
        if "risks" in slot_content and any(x in text for x in ["风险", "问题", "冲突"]):
            slot_content["risks"].append(text)
        if "todos" in slot_content and any(x in text.lower() for x in ["todo", "待办", "下一步"]):
            slot_content["todos"].append(text)
        if "citations" in slot_content:
            slot_content["citations"].append(f.trace_pointer)

    if "disagreements" in slot_content:
        for c in conflicts:
            slot_content["disagreements"].append(f"{c['A']} vs {c['B']}")

    # 去重并保持顺序
    for slot, items in slot_content.items():
        seen = set()
        deduped = []
        for x in items:
            if x not in seen:
                seen.add(x)
                deduped.append(x)
        slot_content[slot] = deduped
    return slot_content


def compute_slot_coverage(
    slot_content: Dict[str, List[str]],
    contract: RetentionContract,
) -> Tuple[Dict[str, float], List[str]]:
    coverage: Dict[str, float] = {}
    violations: List[str] = []

    for slot, rule in contract.slot_constraints.items():
        actual = len(slot_content.get(slot, []))
        if rule.min_items <= 0:
            ratio = 1.0
        else:
            ratio = min(1.0, actual / rule.min_items)
        coverage[slot] = ratio

        if rule.required:
            if ratio < rule.min_coverage_ratio:
                violations.append(
                    f"slot={slot}, ratio={ratio:.2f}, required>={rule.min_coverage_ratio:.2f}"
                )
    return coverage, violations


def summarize_cluster(
    cluster: Cluster,
    fragment_map: Dict[str, Fragment],
    contract: RetentionContract,
) -> Dict[str, object]:
    fragments = [fragment_map[fid] for fid in cluster.fragment_ids if fid in fragment_map]
    conflicts = detect_conflicts(fragments)
    slot_content = build_slot_content(fragments, conflicts, contract)
    coverage, violations = compute_slot_coverage(slot_content, contract)

    summary_lines = []
    for slot in contract.required_slots:
        vals = slot_content.get(slot, [])
        if vals:
            summary_lines.append(f"[{slot}] " + " | ".join(vals[:3]))
    consensus = "\n".join(summary_lines) if summary_lines else "(empty)"

    return {
        "cluster_id": cluster.cluster_id,
        "consensus_summary": consensus,
        "disagreements": conflicts,
        "evidence_pointers": [fragment_map[fid].trace_pointer for fid in cluster.fragment_ids if fid in fragment_map],
        "slot_coverage": coverage,
        "violations": violations,
        "rewrite_history": [],
    }


def build_audit_report(cluster_units: List[Dict[str, object]]) -> Dict[str, object]:
    total = len(cluster_units)
    violation_count = sum(1 for u in cluster_units if u.get("violations"))
    conflict_count = sum(len(u.get("disagreements", [])) for u in cluster_units)

    return {
        "total_clusters": total,
        "clusters_with_violations": violation_count,
        "total_conflict_branches": conflict_count,
        "status": "PASS" if violation_count == 0 else "WARN",
    }
