# Claude Review R11 — 2026-02-11

**Scope**: Codex R11 (ISSUE-36/37 fixes, F-25/F-26) + Codex R12 (test blind spots, F-27/F-28/F-29)
**Commit range**: post-R10 → current HEAD
**Reviewer**: Claude Opus 4.6
**Verdict**: **PASS**

---

## 1  Test Execution

| Check | Result |
|-------|--------|
| `python -m unittest discover` | **51/51 PASS** (0 failures, 0 errors) |
| `qa/validate_scheduler_config.py` | PASS |
| `prototype/run_experiments.py` | 4 scenarios OK |
| `prototype/run_patent_evidence.py` | P-02 + P-03 OK |

## 2  Fix Verification

### F-25 — ISSUE-36 closure: raw view for emergency preemption dimensions

**Change**: `_preempt_low_priority(snapshot, raw_snapshot=None)` now uses
`emergency_view = raw_snapshot or snapshot` for mode/dimension detection.

**Math trace** (test `test_preempt_uses_raw_view_for_emergency_dimension_detection`):
- Smoothed GPU 85% < 95% threshold → would yield `gpu_emergency = False` (old code)
- Raw GPU 96% ≥ 95% → `gpu_emergency = True` (new code via `emergency_view`)
- `hottest_gpu_index = 0` (96% on card 0 from raw)
- `gpu_target_mb = 10000 × 85% = 8500` → `reclaim_needed_gpu_mb = 9600 − 8500 = 1100`
- GPU-HOT score: `effective_gpu_reclaim(1200, idx=0→hottest) / 1100 = 1.091`
- MEM-HEAVY score: `effective_gpu_reclaim(0) / 1100 = 0`
- Sort: GPU-HOT (5, 1.091, −100) > MEM-HEAVY (5, 0, −110) → **GPU-HOT preempted** ✓

**Guard clause** (line 741): `if raw_snapshot is not None and not memory_emergency and not gpu_emergency: return []`
- Prevents preemption during EMERGENCY cooldown ticks with no actual emergency dimension
- `raw_snapshot=None` (legacy direct calls) → guard skipped → backward compat preserved ✓

**Verdict**: CONFIRMED ✓

### F-26 — ISSUE-37 closure: normalized reclaim scoring

**Change**: `resource_reclaim_score()` divides each resource contribution by its own reclaim denominator:
```
mem_score / max(1, reclaim_needed_mb) + gpu_score / max(1, reclaim_needed_gpu_mb)
```

**Math trace** (test `test_mixed_emergency_preempt_score_uses_normalized_resources`):
- Both dimensions in emergency: mem 93% ≥ 92%, GPU 96% ≥ 95%
- `reclaim_needed_mb = 30474.24 − (32768 × 0.85 − 512) = 3133.44` → `mem_denom = 3133.44`
- `reclaim_needed_gpu_mb = 9600 − 8500 = 1100` → `gpu_denom = 1100`
- MIXED-BALANCED: `700/3133.44 + 1200/1100 = 0.223 + 1.091 = 1.314`
- MEM-HEAVY: `2000/3133.44 + 0/1100 = 0.638 + 0 = 0.638`
- **MIXED-BALANCED (1.314) > MEM-HEAVY (0.638)** → correct victim in mixed emergency ✓
- Without normalization: raw MB → MEM-HEAVY (2000) > MIXED-BALANCED (1900) → wrong ✗

**Verdict**: CONFIRMED ✓

### F-27 — Real process lifecycle tests

Two new tests with `dry_run=False`:
1. `test_real_process_completes_and_is_accounted`: subprocess `time.sleep(0.05)`, verifies COMPLETED state + metrics + TASK_FINISHED event
2. `test_real_process_timeout_stops_process_object`: subprocess `time.sleep(2.0)` with `max_runtime_sec=0.02`, verifies timeout + `proc.poll() is not None`

Both exercise the actual `subprocess.Popen` path — first tests to do so. **CONFIRMED** ✓

### F-28 — Long-run randomized stress test

`test_long_run_randomized_snapshots_preserve_state_invariants`:
- 220 ticks, seed=12345, ema_alpha=0.6
- Random snapshots: base 62% ± 12%, periodic spikes (+18% at `i%37==0`)
- 120 tasks with random priorities (1–6), mem (40–420 MB), dry_run_ticks (1–5)
- Per-tick invariants: running_count, pending_count, max_workers, event log bound, metrics monotonicity, unique pending IDs

Covers the ema_alpha=0.6 smoothing path with enough ticks to exercise mode transitions, preemption, and event rotation. **CONFIRMED** ✓

### F-29 — Estimation error tolerance tests

1. `test_estimation_error_overestimate_blocks_large_task_but_small_task_runs`:
   - Task with `estimated_mem_mb=7000` blocked by admission projection
   - Small task (120 MB) still admitted → scheduler doesn't over-block ✓

2. `test_estimation_error_underestimate_then_raw_spike_preempts`:
   - Tick 1: `snap(50,20)` → NORMAL → task (est 50 MB) admitted
   - Tick 2: `snap(97,20)` → raw 97% ≥ 92% → EMERGENCY → task preempted
   - Validates that underestimation is caught by runtime monitoring ✓

**CONFIRMED** ✓

## 3  Code Quality

| Aspect | Assessment |
|--------|------------|
| `_preempt_low_priority` signature | Clean Optional parameter, backward compat via `emergency_view = raw or snapshot` |
| Guard clause | Correctly scoped to tick-path calls only (`raw_snapshot is not None`) |
| `emergency_view.gpu_cards or snapshot.gpu_cards` | Fallback chain works because BUG-3 fix preserves gpu_cards through smoothing |
| `NoCumulativeProjectionScheduler._can_admit` | Signature synced with parent — all new params forwarded ✓ |
| Real process tests | Proper `sch.shutdown()` cleanup, reasonable timeouts |
| Long-run test | Deterministic seed for CI stability, comprehensive invariants |

## 4  Observations (Low / Info)

### OBS-8 (Info): `gpu_cards` fallback uses falsy `or`

```python
gpu_cards = emergency_view.gpu_cards or snapshot.gpu_cards
```

If `emergency_view.gpu_cards` is an empty list `[]` (falsy), it falls through to `snapshot.gpu_cards`. This is fine in practice since empty means no GPUs, but worth noting the `or` semantics.

### OBS-9 (Info): Long-run test uses single seed

The randomized test uses fixed seed 12345. This is good for CI reproducibility. For deeper fuzzing, consider parameterizing with multiple seeds (e.g., `subTest(seed=s)` loop).

## 5  Issue Tracker

| ID | Severity | Status | Description |
|----|----------|--------|-------------|
| ISSUE-36 | Medium | **CLOSED** (F-25) | Preempt used smoothed not raw for emergency dimension |
| ISSUE-37 | Medium | **CLOSED** (F-26) | Mixed score used raw MB units across resources |
| ISSUE-9 | Info | Open | Project direction (scheduler vs memory pipeline) |
| ISSUE-13 | Info | Open | Prior art fake verification (16 items, zero evidence) |
| OBS-8 | Info | New | `gpu_cards` fallback uses falsy `or` |
| OBS-9 | Info | New | Long-run test single seed |

## 6  Test Coverage Summary

| Category | Count | Notes |
|----------|-------|-------|
| Scheduler unit tests | 44 | +7 since R10 |
| Patent evidence tests | 3 | P-01, P-02, P-03 |
| Config validation tests | 4 | unchanged |
| **Total** | **51** | all pass |

New test coverage fills the blind spots identified in R10:
- Real subprocess lifecycle (2 tests)
- Long-run state invariants (1 test, 220 ticks)
- Estimation error tolerance (2 tests)
- ISSUE-36 raw view verification (1 test)
- ISSUE-37 normalized scoring verification (1 test)

## 7  Remaining Gaps

1. **No concurrent stress test**: All tests are single-threaded. No test exercises `tick()` called from multiple threads or with real I/O contention.
2. **No negative/adversarial input**: No test feeds malformed snapshots (NaN, negative values, missing fields beyond None).
3. **Prior art**: ISSUE-13 still unresolved — 16 items marked verified with no evidence. R13 should address this.

## 8  Verdict

**PASS** — F-25 and F-26 correctly close ISSUE-36 and ISSUE-37 with mathematically verified fixes. F-27/F-28/F-29 close the test blind spots flagged in R10. Code is production-ready with 51/51 tests green, config/experiments/patent evidence all passing.

**Recommendation**: Proceed to R13 (prior art rebuild + patent document rewrite + route decision). The 3 core protection points agreed with the user are:
1. Per-GPU affinity admission projection (bound/unbound split)
2. Bottleneck resource-directed preemption (hottest card + affinity weights + dual reclaim targets + normalized scoring)
3. Dual-view mode detection + same-tick cumulative projection as unified admission scheme
