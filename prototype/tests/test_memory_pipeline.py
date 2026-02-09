from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_pipeline import (
    Cluster,
    RetentionContract,
    SlotConstraint,
    assign_or_create_cluster,
    detect_conflicts,
    ingest_fragment,
    summarize_cluster,
)


def make_contract() -> RetentionContract:
    slot_constraints = {
        "facts": SlotConstraint(required=True, min_coverage_ratio=0.5, min_items=1),
        "disagreements": SlotConstraint(required=True, min_coverage_ratio=1.0, min_items=1),
    }
    return RetentionContract(
        contract_id="test",
        version="v1.0",
        domain="patent_writing",
        required_slots=["facts", "disagreements"],
        slot_constraints=slot_constraints,
        source_weights={"a": 1.0},
        topic_allowlist=[],
        topic_blocklist=[],
        global_token_budget=512,
        per_cluster_min_tokens=32,
        per_cluster_max_tokens=256,
        max_rewrite_rounds=2,
        require_entailment_check=True,
        require_conflict_check=True,
    )


class MemoryPipelineTests(unittest.TestCase):
    def test_cluster_assignment_merge(self) -> None:
        clusters: dict[str, Cluster] = {}
        f1 = ingest_fragment("F1", "步骤1：参数A=1", "agent1", "trace://1")
        f2 = ingest_fragment("F2", "步骤2：参数A=1", "agent2", "trace://2")
        c1 = assign_or_create_cluster(f1, clusters, similarity_threshold=0.2)
        c2 = assign_or_create_cluster(f2, clusters, similarity_threshold=0.2)
        self.assertEqual(c1, c2)
        self.assertEqual(len(clusters[c1].fragment_ids), 2)

    def test_conflict_detection(self) -> None:
        f1 = ingest_fragment("F1", "参数A=0.4", "agent1", "trace://1")
        f2 = ingest_fragment("F2", "参数A=0.6", "agent2", "trace://2")
        conflicts = detect_conflicts([f1, f2])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("a=0.4", conflicts[0]["A"])

    def test_summary_has_violation_without_disagreement(self) -> None:
        contract = make_contract()
        f1 = ingest_fragment("F1", "普通事实文本", "agent1", "trace://1")
        cluster = Cluster(cluster_id="C-0001", fragment_ids=["F1"], centroid=f1.embedding)
        unit = summarize_cluster(cluster, {"F1": f1}, contract)
        self.assertTrue(unit["violations"])


if __name__ == "__main__":
    unittest.main()
