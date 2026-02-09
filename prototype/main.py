from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from memory_pipeline import (
    Cluster,
    RetentionContract,
    SlotConstraint,
    assign_or_create_cluster,
    build_audit_report,
    ingest_fragment,
    summarize_cluster,
)


ROOT = Path(__file__).resolve().parents[1]


def load_contract(domain: str = "patent_writing") -> RetentionContract:
    examples_path = ROOT / "spec" / "retention_contract_examples.json"
    data = json.loads(examples_path.read_text(encoding="utf-8"))
    match = next((x for x in data if x["domain"] == domain), None)
    if match is None:
        raise ValueError(f"Contract domain not found: {domain}")

    slot_constraints = {
        k: SlotConstraint(
            required=v["required"],
            min_coverage_ratio=v["min_coverage_ratio"],
            min_items=v["min_items"],
            note=v.get("note", ""),
        )
        for k, v in match["slot_constraints"].items()
    }
    return RetentionContract(
        contract_id=match["contract_id"],
        version=match["version"],
        domain=match["domain"],
        required_slots=match["required_slots"],
        slot_constraints=slot_constraints,
        source_weights=match["source_weights"],
        topic_allowlist=match["topic_policy"]["allowlist"],
        topic_blocklist=match["topic_policy"]["blocklist"],
        global_token_budget=match["length_constraints"]["global_token_budget"],
        per_cluster_min_tokens=match["length_constraints"]["per_cluster_min_tokens"],
        per_cluster_max_tokens=match["length_constraints"]["per_cluster_max_tokens"],
        max_rewrite_rounds=match["validation_policy"]["max_rewrite_rounds"],
        require_entailment_check=match["validation_policy"]["require_entailment_check"],
        require_conflict_check=match["validation_policy"]["require_conflict_check"],
    )


def sample_fragments():
    return [
        {
            "id": "F-001",
            "content": "步骤1：收集碎片并记录参数A=0.4，风险：可能遗漏证据。",
            "agent": "planner_agent",
            "trace": "trace://input/001",
            "topics": ["采集", "参数", "风险"],
        },
        {
            "id": "F-002",
            "content": "步骤2：进行候选并簇，参数A=0.5，决定采用双阶段检索。",
            "agent": "executor_agent",
            "trace": "trace://input/002",
            "topics": ["并簇", "检索", "决策"],
        },
        {
            "id": "F-003",
            "content": "工具结果：结构检查 PASS；下一步 TODO：补充权利要求映射。",
            "agent": "qa_agent",
            "trace": "trace://input/003",
            "topics": ["工具输出", "待办"],
        },
    ]


def run_pipeline() -> Dict[str, object]:
    contract = load_contract("patent_writing")

    clusters: Dict[str, Cluster] = {}
    fragment_map = {}

    for row in sample_fragments():
        f = ingest_fragment(
            fragment_id=row["id"],
            content=row["content"],
            source_agent=row["agent"],
            trace_pointer=row["trace"],
            confidence=1.0,
            topics=row["topics"],
        )
        fragment_map[f.fragment_id] = f
        assign_or_create_cluster(f, clusters, similarity_threshold=0.30)

    units: List[Dict[str, object]] = []
    for cid in sorted(clusters.keys()):
        units.append(summarize_cluster(clusters[cid], fragment_map, contract))

    audit = build_audit_report(units)
    return {"cluster_units": units, "audit": audit}


if __name__ == "__main__":
    result = run_pipeline()
    print(json.dumps(result, ensure_ascii=False, indent=2))
