from __future__ import annotations

import csv
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Tuple

from main import load_contract
from memory_pipeline import Cluster, assign_or_create_cluster, ingest_fragment, summarize_cluster


ROOT = Path(__file__).resolve().parents[1]
FIGURES_DIR = ROOT / "figures"
CSV_PATH = FIGURES_DIR / "experiment_metrics.csv"
JSON_PATH = FIGURES_DIR / "experiment_metrics.json"


def token_count(text: str) -> int:
    return len([x for x in text.replace("\n", " ").split(" ") if x.strip()])


def generate_synthetic_fragments(seed: int = 7) -> List[Dict[str, object]]:
    random.seed(seed)
    rows: List[Dict[str, object]] = []
    topics = ["聚类", "契约", "冲突"]
    values = {
        "聚类": ["A=0.4", "A=0.5"],
        "契约": ["B=strict", "B=loose"],
        "冲突": ["C=keep", "C=merge"],
    }
    idx = 1
    for topic in topics:
        for i in range(16):
            value = values[topic][i % 2]
            content = f"步骤{i+1}：主题{topic}，参数{value}，风险：需要校验。"
            rows.append(
                {
                    "id": f"F-{idx:04d}",
                    "content": content,
                    "agent": f"agent_{(i % 3) + 1}",
                    "trace": f"trace://synthetic/{idx:04d}",
                    "topics": [topic],
                }
            )
            idx += 1
    random.shuffle(rows)
    return rows


def run_once(seed: int = 7) -> Tuple[Dict[str, float], List[Dict[str, object]]]:
    contract = load_contract("patent_writing")
    rows = generate_synthetic_fragments(seed=seed)

    clusters: Dict[str, Cluster] = {}
    fragment_map = {}

    t0 = time.perf_counter()
    for row in rows:
        f = ingest_fragment(
            fragment_id=row["id"],
            content=row["content"],
            source_agent=row["agent"],
            trace_pointer=row["trace"],
            confidence=1.0,
            topics=row["topics"],
        )
        fragment_map[f.fragment_id] = f
        assign_or_create_cluster(f, clusters, similarity_threshold=0.35)

    units = [summarize_cluster(clusters[cid], fragment_map, contract) for cid in sorted(clusters.keys())]
    elapsed_ms = (time.perf_counter() - t0) * 1000

    original_tokens = sum(token_count(r["content"]) for r in rows)
    summary_tokens = sum(token_count(u["consensus_summary"]) for u in units)
    compression_rate = 1.0 - (summary_tokens / original_tokens if original_tokens else 0.0)

    expected_conflicts = 3.0
    detected_conflicts = float(sum(1 for u in units if len(u["disagreements"]) > 0))
    conflict_retention_rate = min(1.0, detected_conflicts / expected_conflicts)

    required_slots = sum(
        1
        for _ in units
        for slot, rule in contract.slot_constraints.items()
        if rule.required
    )
    pass_slots = sum(
        1
        for u in units
        for slot, rule in contract.slot_constraints.items()
        if rule.required and u["slot_coverage"].get(slot, 0.0) >= rule.min_coverage_ratio
    )
    preference_compliance_rate = (pass_slots / required_slots) if required_slots else 1.0

    metrics = {
        "run_seed": float(seed),
        "fragments": float(len(rows)),
        "clusters": float(len(units)),
        "token_compression_rate": round(compression_rate, 4),
        "conflict_retention_rate": round(conflict_retention_rate, 4),
        "preference_compliance_rate": round(preference_compliance_rate, 4),
        "runtime_ms": round(elapsed_ms, 2),
    }
    return metrics, units


def write_outputs(metrics: Dict[str, float], units: List[Dict[str, object]]) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)

    payload = {"metrics": metrics, "sample_cluster_unit": units[0] if units else {}}
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    metrics, units = run_once(seed=7)
    write_outputs(metrics, units)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"[OK] wrote: {CSV_PATH}")
    print(f"[OK] wrote: {JSON_PATH}")


if __name__ == "__main__":
    main()
