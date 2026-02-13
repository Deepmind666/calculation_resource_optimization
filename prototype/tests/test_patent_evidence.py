from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_patent_evidence import (  # noqa: E402
    build_flattened_rows,
    run_p02_mode_stability_ablation,
    run_p03_cumulative_admission_ablation,
)


class PatentEvidenceTests(unittest.TestCase):
    def test_p02_dual_view_reduces_emergency_response_delay(self) -> None:
        p02 = run_p02_mode_stability_ablation()
        variants = {item["variant"]: item for item in p02["variants"]}  # type: ignore[index]
        dual_view = variants["dual_view_raw_plus_ema"]
        ema_only = variants["ema_only_alpha_0_3_no_raw_bypass"]

        self.assertEqual(dual_view["response_delay_ticks"], 0)
        self.assertIsNotNone(ema_only["response_delay_ticks"])
        self.assertGreater(ema_only["response_delay_ticks"], dual_view["response_delay_ticks"])
        self.assertLess(dual_view["first_emergency_tick"], ema_only["first_emergency_tick"])

    def test_p03_cumulative_projection_reduces_over_issue(self) -> None:
        p03 = run_p03_cumulative_admission_ablation()
        variants = {item["variant"]: item for item in p03["variants"]}  # type: ignore[index]
        with_cumulative = variants["with_cumulative_projection"]
        without_cumulative = variants["without_cumulative_projection_baseline"]

        self.assertLess(with_cumulative["admitted_tasks"], without_cumulative["admitted_tasks"])
        self.assertFalse(with_cumulative["breach_limit"])
        self.assertTrue(without_cumulative["breach_limit"])
        self.assertGreater(p03["over_issued_tasks_without_cumulative"], 0)  # type: ignore[index]
        self.assertGreater(p03["over_issue_rate_without_cumulative"], 0.0)  # type: ignore[index]

    def test_flattened_rows_include_p02_and_p03(self) -> None:
        p02 = run_p02_mode_stability_ablation()
        p03 = run_p03_cumulative_admission_ablation()
        rows = build_flattened_rows(p02, p03)

        p02_rows = [r for r in rows if r["evidence_id"] == "P-02"]
        p03_rows = [r for r in rows if r["evidence_id"] == "P-03"]
        self.assertEqual(len(p02_rows), 2)
        self.assertEqual(len(p03_rows), 2)
        self.assertTrue(all("response_delay_ticks" in row for row in p02_rows))
        self.assertTrue(all("over_issue_rate_without_cumulative" in row for row in p03_rows))


if __name__ == "__main__":
    unittest.main()
