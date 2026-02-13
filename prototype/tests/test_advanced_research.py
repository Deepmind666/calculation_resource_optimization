from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_advanced_research import (  # noqa: E402
    apply_eventful_threshold_bias,
    _sample_gpu_peak_percent,
    escalate_real_baseline_params,
    need_eventful_retry,
    plan_eventful_scheduler_thresholds,
    plan_real_baseline_params,
    run_p04_per_gpu_affinity_ablation,
    run_p05_preemption_ablation,
    run_real_machine_baseline_until_eventful,
    run_multiseed_confidence_summary,
    summarize_real_baseline_runs,
    update_eventful_threshold_bias,
)


class AdvancedResearchTests(unittest.TestCase):
    def test_sample_gpu_peak_percent_skips_absurd_rows(self) -> None:
        fake_out = "\n".join(
            [
                "7000, 0.000001",
                "3000, 10000",
            ]
        )
        with patch("run_advanced_research.shutil.which", return_value="nvidia-smi"), patch(
            "run_advanced_research.subprocess.check_output",
            return_value=fake_out,
        ):
            peak = _sample_gpu_peak_percent()
        self.assertIsNotNone(peak)
        assert peak is not None
        self.assertGreaterEqual(peak, 0.0)
        self.assertLessEqual(peak, 100.0)
        self.assertAlmostEqual(peak, 30.0, places=3)

    def test_p04_per_gpu_projection_reduces_false_blocks(self) -> None:
        out = run_p04_per_gpu_affinity_ablation(trials=400, seed=123)
        self.assertGreater(out["safe_cases"], 0)
        self.assertGreater(out["aggregate_false_block_rate"], out["per_gpu_false_block_rate"])
        self.assertGreater(out["false_block_reduction"], 0.0)
        self.assertIn("scenario_breakdown", out)
        breakdown = out["scenario_breakdown"]
        self.assertEqual(
            sum(int(v["trials"]) for v in breakdown.values()),
            400,
        )
        self.assertEqual(
            sum(int(v["safe_cases"]) for v in breakdown.values()),
            out["safe_cases"],
        )
        self.assertGreater(
            breakdown["other_card_only"]["aggregate_false_block_rate"],
            breakdown["other_card_only"]["per_gpu_false_block_rate"],
        )

    def test_p05_normalized_preemption_beats_random_baseline(self) -> None:
        out = run_p05_preemption_ablation(trials=300, seed=123, tight_preempt_limit=5)
        self.assertGreaterEqual(out["normalized_better_or_equal_random_rate"], 0.6)
        self.assertGreaterEqual(out["normalized_better_or_equal_raw_rate"], 0.55)
        self.assertEqual(out["tight_preempt_limit"], 5)
        self.assertIn("recovery_rate_normalized_tight", out)
        self.assertIn("recovery_rate_raw_mb_tight", out)
        self.assertIn("normalized_better_or_equal_random_rate_tight", out)
        self.assertGreaterEqual(out["normalized_better_or_equal_random_rate_tight"], 0.5)
        self.assertGreaterEqual(out["normalized_better_or_equal_raw_rate_tight"], 0.5)

    def test_multiseed_confidence_summary_has_ci_bounds(self) -> None:
        out = run_multiseed_confidence_summary(
            trials_per_seed=120,
            seed_runs=4,
            base_seed=123,
            seed_step=17,
            tight_preempt_limit=5,
        )
        self.assertEqual(out["seed_runs"], 4)
        self.assertEqual(out["trials_per_seed"], 120)
        self.assertEqual(len(out["seed_list"]), 4)
        self.assertEqual(len(out["per_seed"]), 4)

        for metric_name, summary in out["metrics"].items():
            self.assertIn("mean", summary, metric_name)
            self.assertIn("ci95_low", summary, metric_name)
            self.assertIn("ci95_high", summary, metric_name)
            self.assertLessEqual(summary["ci95_low"], summary["mean"], metric_name)
            self.assertGreaterEqual(summary["ci95_high"], summary["mean"], metric_name)
            self.assertGreaterEqual(summary["stddev"], 0.0, metric_name)

    def test_real_baseline_summary_has_mode_ci_metrics(self) -> None:
        runs = [
            {
                "results": [
                    {
                        "mode": "A_no_scheduler",
                        "completion_rate": 1.0,
                        "wall_time_sec": 2.0,
                        "throughput_tps": 5.0,
                        "nonzero_exit_count": 0.0,
                        "peak_memory_pct": None,
                    },
                    {
                        "mode": "C_dynamic_scheduler",
                        "completion_rate": 1.0,
                        "wall_time_sec": 3.0,
                        "throughput_tps": 3.3,
                        "nonzero_exit_count": 0.0,
                        "blocked_event_total": 12.0,
                        "unfinished_tasks": 0.0,
                        "scheduler_timeout_hit": 0.0,
                        "stalled_no_admission": 0.0,
                    },
                ]
            },
            {
                "results": [
                    {
                        "mode": "A_no_scheduler",
                        "completion_rate": 1.0,
                        "wall_time_sec": 2.4,
                        "throughput_tps": 4.2,
                        "nonzero_exit_count": 0.0,
                        "peak_memory_pct": None,
                    },
                    {
                        "mode": "C_dynamic_scheduler",
                        "completion_rate": 0.9,
                        "wall_time_sec": 3.6,
                        "throughput_tps": 2.8,
                        "nonzero_exit_count": 1.0,
                        "blocked_event_total": 15.0,
                        "unfinished_tasks": 1.0,
                        "scheduler_timeout_hit": 1.0,
                        "stalled_no_admission": 1.0,
                    },
                ]
            },
        ]
        out = summarize_real_baseline_runs(runs)
        self.assertEqual(out["repeat_runs"], 2)
        self.assertIn("A_no_scheduler", out["by_mode"])
        self.assertIn("C_dynamic_scheduler", out["by_mode"])

        a_wall = out["by_mode"]["A_no_scheduler"]["wall_time_sec"]
        self.assertEqual(a_wall["n"], 2.0)
        self.assertAlmostEqual(a_wall["mean"], 2.2, places=6)
        self.assertLessEqual(a_wall["ci95_low"], a_wall["mean"])
        self.assertGreaterEqual(a_wall["ci95_high"], a_wall["mean"])

        a_peak_mem = out["by_mode"]["A_no_scheduler"]["peak_memory_pct"]
        self.assertEqual(a_peak_mem["n"], 0.0)
        self.assertIsNone(a_peak_mem["mean"])

        c_blocked = out["by_mode"]["C_dynamic_scheduler"]["blocked_event_total"]
        self.assertEqual(c_blocked["n"], 2.0)
        self.assertAlmostEqual(c_blocked["mean"], 13.5, places=6)
        c_timeout_hit = out["by_mode"]["C_dynamic_scheduler"]["scheduler_timeout_hit"]
        self.assertEqual(c_timeout_hit["n"], 2.0)
        self.assertAlmostEqual(c_timeout_hit["mean"], 0.5, places=6)

    def test_plan_real_baseline_params_strengthens_weak_inputs(self) -> None:
        out = plan_real_baseline_params(
            task_count=18,
            duration_sec=2.0,
            base_mem_mb=96,
            fixed_workers=4,
            host_total_mem_mb=16384.0,
        )
        self.assertGreaterEqual(out["duration_sec"], 6.0)
        self.assertGreaterEqual(out["base_mem_mb"], 1024)
        self.assertGreaterEqual(out["task_count"], 5)
        self.assertLessEqual(out["task_count"], 18)
        self.assertTrue(out["notes"])

    def test_plan_real_baseline_params_reduces_oversized_task_count(self) -> None:
        out = plan_real_baseline_params(
            task_count=20,
            duration_sec=8.0,
            base_mem_mb=2048,
            fixed_workers=4,
            host_total_mem_mb=16384.0,
        )
        self.assertLess(out["task_count"], 20)
        self.assertGreaterEqual(out["task_count"], 5)
        self.assertGreaterEqual(out["base_mem_mb"], 1024)

    def test_need_eventful_retry_flags(self) -> None:
        retry, reason = need_eventful_retry({"low_signal_dynamic": 1, "emergency_signal_missing": 0})
        self.assertTrue(retry)
        self.assertEqual(reason, "low_signal_dynamic")
        retry, reason = need_eventful_retry({"low_signal_dynamic": 0, "emergency_signal_missing": 1})
        self.assertTrue(retry)
        self.assertEqual(reason, "missing_emergency_signal")
        retry, reason = need_eventful_retry({"low_signal_dynamic": 0, "emergency_signal_missing": 0})
        self.assertFalse(retry)
        self.assertEqual(reason, "satisfied")

    def test_need_eventful_retry_can_require_completion(self) -> None:
        retry, reason = need_eventful_retry(
            {"low_signal_dynamic": 0, "emergency_signal_missing": 0, "completed": 0},
            require_completion=True,
            min_completed=1,
        )
        self.assertTrue(retry)
        self.assertEqual(reason, "insufficient_completion")
        retry, reason = need_eventful_retry(
            {"low_signal_dynamic": 0, "emergency_signal_missing": 0, "completed": 2},
            require_completion=True,
            min_completed=1,
        )
        self.assertFalse(retry)
        self.assertEqual(reason, "satisfied")

    def test_escalate_real_baseline_params_increases_pressure(self) -> None:
        out = escalate_real_baseline_params(
            task_count=8,
            duration_sec=6.0,
            base_mem_mb=1024,
            fixed_workers=4,
            host_total_mem_mb=16384.0,
        )
        self.assertGreaterEqual(out["duration_sec"], 8.0)
        self.assertGreaterEqual(out["base_mem_mb"], 1024)
        self.assertGreaterEqual(out["task_count"], 5)
        self.assertTrue(
            (out["duration_sec"] > 6.0) or (out["base_mem_mb"] > 1024) or (out["task_count"] > 8)
        )

    def test_plan_eventful_scheduler_thresholds_are_valid_and_tighten(self) -> None:
        t0 = plan_eventful_scheduler_thresholds(0)
        t1 = plan_eventful_scheduler_thresholds(1)
        t2 = plan_eventful_scheduler_thresholds(2)
        for t in (t0, t1, t2):
            self.assertLess(t["memory_high_pct"], t["memory_emergency_pct"])
            self.assertGreater(t["memory_high_pct"], 0.0)
            self.assertGreater(t["memory_emergency_pct"], 0.0)
            self.assertLessEqual(t["memory_emergency_pct"], 100.0)
        self.assertGreaterEqual(t0["memory_high_pct"], t1["memory_high_pct"])
        self.assertGreaterEqual(t1["memory_high_pct"], t2["memory_high_pct"])
        self.assertGreaterEqual(t0["memory_emergency_pct"], t1["memory_emergency_pct"])
        self.assertGreaterEqual(t1["memory_emergency_pct"], t2["memory_emergency_pct"])

    def test_apply_eventful_threshold_bias_is_reasonable(self) -> None:
        base = plan_eventful_scheduler_thresholds(0)
        relaxed = apply_eventful_threshold_bias(base, 8.0)
        tightened = apply_eventful_threshold_bias(base, -6.0)
        self.assertGreater(relaxed["memory_high_pct"], base["memory_high_pct"])
        self.assertGreater(relaxed["memory_emergency_pct"], base["memory_emergency_pct"])
        self.assertLess(tightened["memory_high_pct"], base["memory_high_pct"])
        self.assertLess(tightened["memory_emergency_pct"], base["memory_emergency_pct"])
        self.assertLess(relaxed["memory_high_pct"], relaxed["memory_emergency_pct"])
        self.assertLess(tightened["memory_high_pct"], tightened["memory_emergency_pct"])
        self.assertGreaterEqual(tightened["memory_high_pct"], 50.0)
        self.assertLessEqual(relaxed["memory_emergency_pct"], 99.0)

    def test_update_eventful_threshold_bias_rules(self) -> None:
        self.assertEqual(update_eventful_threshold_bias(0.0, "insufficient_completion"), 8.0)
        self.assertEqual(update_eventful_threshold_bias(19.0, "insufficient_completion"), 20.0)
        self.assertEqual(update_eventful_threshold_bias(0.0, "low_signal_dynamic"), -4.0)
        self.assertEqual(update_eventful_threshold_bias(-19.0, "missing_emergency_signal"), -20.0)
        self.assertEqual(update_eventful_threshold_bias(3.0, "missing_dynamic_row"), -1.0)
        self.assertEqual(update_eventful_threshold_bias(1.5, "satisfied"), 1.5)

    def test_run_real_machine_baseline_until_eventful_stops_early(self) -> None:
        first = {
            "host_total_mem_mb": 16384.0,
            "results": [
                {"mode": "A_no_scheduler"},
                {"mode": "B_fixed_concurrency"},
                {
                    "mode": "C_dynamic_scheduler",
                    "low_signal_dynamic": 1,
                    "emergency_signal_missing": 1,
                    "started_total": 0,
                    "emergency_ticks": 0,
                    "preempted_total": 0,
                },
            ],
        }
        second = {
            "host_total_mem_mb": 16384.0,
            "results": [
                {"mode": "A_no_scheduler"},
                {"mode": "B_fixed_concurrency"},
                {
                    "mode": "C_dynamic_scheduler",
                    "low_signal_dynamic": 0,
                    "emergency_signal_missing": 0,
                    "started_total": 3,
                    "emergency_ticks": 1,
                    "preempted_total": 1,
                },
            ],
        }
        with patch("run_advanced_research.run_real_machine_baseline", side_effect=[first, second]) as mocked:
            out = run_real_machine_baseline_until_eventful(
                max_attempts=4,
                task_count=8,
                duration_sec=6.0,
                base_mem_mb=1024,
                fixed_workers=4,
                seed=123,
                max_scheduler_wall_sec=20.0,
            )
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(out["attempts_executed"], 2)
        self.assertEqual(out["eventful_achieved"], 1)
        self.assertEqual(len(out["attempts"]), 2)
        self.assertEqual(out["final_result"]["results"][-1]["mode"], "C_dynamic_scheduler")
        first_call = mocked.call_args_list[0].kwargs
        second_call = mocked.call_args_list[1].kwargs
        self.assertIn("dynamic_memory_high_pct", first_call)
        self.assertIn("dynamic_memory_emergency_pct", first_call)
        self.assertLessEqual(second_call["dynamic_memory_high_pct"], first_call["dynamic_memory_high_pct"])
        self.assertLessEqual(second_call["dynamic_memory_emergency_pct"], first_call["dynamic_memory_emergency_pct"])
        self.assertGreaterEqual(second_call["task_count"], first_call["task_count"])

    def test_run_real_machine_baseline_until_eventful_with_completion_requirement(self) -> None:
        first = {
            "host_total_mem_mb": 16384.0,
            "results": [
                {"mode": "A_no_scheduler"},
                {"mode": "B_fixed_concurrency"},
                {
                    "mode": "C_dynamic_scheduler",
                    "low_signal_dynamic": 0,
                    "emergency_signal_missing": 0,
                    "completed": 0,
                    "started_total": 2,
                    "emergency_ticks": 2,
                    "preempted_total": 1,
                    "scheduler_timeout_hit": 1,
                },
            ],
        }
        second = {
            "host_total_mem_mb": 16384.0,
            "results": [
                {"mode": "A_no_scheduler"},
                {"mode": "B_fixed_concurrency"},
                {
                    "mode": "C_dynamic_scheduler",
                    "low_signal_dynamic": 0,
                    "emergency_signal_missing": 0,
                    "completed": 2,
                    "started_total": 3,
                    "emergency_ticks": 1,
                    "preempted_total": 1,
                    "scheduler_timeout_hit": 0,
                },
            ],
        }
        with patch("run_advanced_research.run_real_machine_baseline", side_effect=[first, second]) as mocked:
            out = run_real_machine_baseline_until_eventful(
                max_attempts=3,
                task_count=8,
                duration_sec=6.0,
                base_mem_mb=1024,
                fixed_workers=4,
                seed=123,
                max_scheduler_wall_sec=12.0,
                require_completion=True,
                min_completed=1,
            )
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(out["eventful_achieved"], 1)
        self.assertEqual(out["attempts"][0]["retry_reason"], "insufficient_completion")
        self.assertEqual(out["attempts"][1]["retry_reason"], "satisfied")
        first_call = mocked.call_args_list[0].kwargs
        second_call = mocked.call_args_list[1].kwargs
        self.assertGreater(second_call["max_scheduler_wall_sec"], first_call["max_scheduler_wall_sec"])
        self.assertGreaterEqual(second_call["dynamic_memory_high_pct"], first_call["dynamic_memory_high_pct"])
        self.assertGreaterEqual(second_call["dynamic_memory_emergency_pct"], first_call["dynamic_memory_emergency_pct"])
        self.assertEqual(second_call["task_count"], first_call["task_count"])
        self.assertEqual(second_call["base_mem_mb"], first_call["base_mem_mb"])


if __name__ == "__main__":
    unittest.main()
