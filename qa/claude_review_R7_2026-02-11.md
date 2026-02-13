# Claude Review R7 — Deep Evaluation

- Timestamp: 2026-02-11 01:00 +08:00
- Reviewer: Claude (Opus 4.6)
- Scope: Codex work since R6 PASS — F-14/F-15/F-16, experiment scripts, patent evidence scripts, audit documents
- Baseline commit: `eed9a68` (last committed) + uncommitted working tree changes
- Files reviewed: 15 files across `prototype/`, `spec/`, `qa/`, `figures/`

---

## 1. Validation Results

| Check | Result |
|---|---|
| Unit tests | **32/32 PASS** |
| Config validation | **PASS** |
| Structure check | **PASS** |
| `run_experiments.py` | **Executes OK**, outputs regenerated |
| `run_patent_evidence.py` | **Executes OK**, outputs regenerated |

---

## 2. Fix Verification: F-14 / F-15 / F-16

### F-14 [High] GPU sampling robustness — skip N/A rows

**Claim**: `_sample_gpu()` silently returned `{}` when any nvidia-smi row contained "N/A", disabling GPU guard even if other cards had valid data.

**Code verification** (`prototype/resource_scheduler.py:170-186`):
```python
for idx, line in enumerate(out.strip().splitlines()):
    ...
    try:
        util = float(parts[0])
        used_mb = float(parts[1])
        total_mb = float(parts[2])
    except ValueError:
        continue          # <-- per-row skip instead of whole-function failure
    if total_mb <= 0:
        continue          # <-- guard against division-by-zero
```

**Math trace** (test input `"20, 1000, 10000\nN/A, N/A, N/A\n30, 7000, 8000\n"`):
- Row 0: util=20, used=1000, total=10000 → mem_pct=10% → valid
- Row 1: `float("N/A")` raises ValueError → skip
- Row 2: util=30, used=7000, total=8000 → mem_pct=87.5% → valid
- Worst card: row 2 (87.5% > 10%)
- Expected output: `gpu_memory_percent=87.5`, `gpu_memory_used_mb=7000`, `gpu_memory_total_mb=8000`, `gpu_util_percent=30`

**Test verification** (`prototype/tests/test_resource_scheduler.py:375-387`):
`test_gpu_monitor_skips_malformed_rows` — provides mixed valid + "N/A" rows, asserts correct worst-card result. **Assertions match math trace. PASS.**

**Verdict: Genuine fix. ✓**

---

### F-15 [Medium] GPU threshold relation validation

**Claim**: Config accepted `gpu_memory_high_pct=96` + `gpu_memory_emergency_pct=95` without error, creating semantically invalid policy (HIGH threshold above EMERGENCY).

**Code verification**:
- Core validation (`prototype/resource_scheduler.py:743`):
  ```python
  if cfg.gpu_memory_high_pct >= cfg.gpu_memory_emergency_pct:
      raise ValueError("gpu_memory_high_pct must be < gpu_memory_emergency_pct.")
  ```
- QA validation (`qa/validate_scheduler_config.py:109-110`):
  ```python
  if float(cfg["gpu_memory_high_pct"]) >= float(cfg["gpu_memory_emergency_pct"]):
      fail("gpu_memory_high_pct must be < gpu_memory_emergency_pct.")
  ```
- Note: memory (`line 739-740`) and CPU (`line 741-742`) already had this check. GPU was the missing case.

**Test verification** (`prototype/tests/test_resource_scheduler.py:592-625`):
`test_invalid_gpu_threshold_relation_rejected` — creates full valid config with `gpu_memory_high_pct=96.0`, `gpu_memory_emergency_pct=95.0`, asserts `ValueError` from `load_scheduler_config`. **PASS.**

**Verdict: Genuine fix. ✓**

---

### F-16 [Medium] Blocked metrics split — event count vs unique task count

**Claim**: `blocked_total` measured blocking *events* (same task blocked on multiple ticks = multiple increments). Users could not distinguish "how many unique tasks were ever blocked".

**Code verification**:
- New field: `SchedulerMetrics.blocked_task_total: int = 0` (line 96)
- Tracking set: `self._blocked_task_ids: Set[str] = set()` (line 222)
- Counting logic (lines 294-297):
  ```python
  self.metrics.blocked_total += 1           # always increment (event)
  if task.task_id not in self._blocked_task_ids:
      self._blocked_task_ids.add(task.task_id)
      self.metrics.blocked_task_total += 1   # increment once per unique task
  ```

**Math trace** (test scenario 1: same task, 2 ticks):
- Tick 1: BLOCK-ONCE blocked → blocked_total=1, _blocked_task_ids={"BLOCK-ONCE"}, blocked_task_total=1
- Tick 2: BLOCK-ONCE blocked again → blocked_total=2, already in set → blocked_task_total stays 1

**Math trace** (test scenario 2: 2 different tasks, 1 tick):
- Tick 1: BLOCK-A blocked → blocked_total=1, blocked_task_total=1
- Tick 1: BLOCK-B blocked → blocked_total=2, blocked_task_total=2

**Test verification**:
- `test_blocked_metrics_split_event_and_unique_task_count` (line 307): Same task, 2 ticks → `blocked_total=2, blocked_task_total=1`. **PASS.**
- `test_blocked_metrics_unique_count_with_multiple_tasks` (line 326): 2 tasks, 1 tick → `blocked_total=2, blocked_task_total=2`. **PASS.**

**Cross-validation with experiment output**:
- `high_pressure`: `blocked_event_total=100, blocked_task_total=10, unique_blocked_tasks=10` — all 10 tasks blocked every tick (10×10=100 events), 10 unique tasks ✓
- `burst_then_recover`: `blocked_event_total=18, blocked_task_total=7, unique_blocked_tasks=7` — consistent ✓

**Verdict: Genuine fix. ✓**

---

## 3. Patent Evidence Scripts Review

### P-02 Ablation: Dual-View vs EMA-Only

**Design**: `EmaOnlyModeScheduler` overrides `_evaluate_mode` to use smoothed snapshot for emergency checks (ignoring raw). Compared against production `DynamicTaskScheduler` that uses raw for emergency.

**Math verification** (raw_memory_series = [82, 83, 97, 97, 97, 97, 83, 82], alpha=0.3, emergency=92%):

| Tick | Raw (%) | EMA Smoothed (%) | Dual-View Mode | EMA-Only Mode |
|---:|---:|---:|---|---|
| 1 | 82.0 | 82.0 | NORMAL | NORMAL |
| 2 | 83.0 | 82.3 | NORMAL | NORMAL |
| 3 | 97.0 | 86.7 | **EMERGENCY** (raw≥92) | HIGH (86.7≥85) |
| 4 | 97.0 | 89.8 | EMERGENCY | HIGH |
| 5 | 97.0 | 92.0 | EMERGENCY | HIGH |
| 6 | 97.0 | 93.5 | EMERGENCY | **EMERGENCY** (93.5≥92) |

- Dual-view delay = 0 ticks (reacts at tick 3 when raw first exceeds 92%)
- EMA-only delay = 3 ticks (doesn't cross 92% until tick 6)

**Matches script output.** The ablation conclusively demonstrates P-02's value. ✓

### P-03 Ablation: Cumulative vs No-Cumulative Projection

**Design**: `NoCumulativeProjectionScheduler` overrides `_can_admit` to always pass `planned_extra=0`, simulating no same-tick cumulative tracking. Uses real-mode (non-dry-run) with actual subprocesses.

**Math verification** (memory=78%, total=16384MB, used=12779.52MB, reserve=512, 4 tasks × 800MB):

| Task | Cumulative: projected_mem_pct | No-Cumul: projected_mem_pct | Result |
|---:|---:|---:|---|
| 1 | (12779.52 + 0 + 800 + 512)/16384 = 85.99% | 85.99% | Both ADMIT |
| 2 | (12779.52 + 800 + 800 + 512)/16384 = 90.89% | 85.99% (no accumulation) | Both ADMIT |
| 3 | (12779.52 + 1600 + 800 + 512)/16384 = 95.80% | 85.99% | Cumul: BLOCK; NoCumul: ADMIT |
| 4 | same | 85.99% | Cumul: BLOCK; NoCumul: ADMIT |

- With cumulative: 2 admitted, peak=90.89% (safe)
- Without: 4 admitted, actual peak=100.66% (**breach**)
- Over-issue rate = 2/4 = 0.5

**Matches script output.** The ablation conclusively demonstrates P-03's value. ✓

### Test Coverage

`test_patent_evidence.py` (3 tests) properly asserts:
1. P-02: `response_delay_ticks=0` for dual-view, `>0` for EMA-only
2. P-03: cumulative admits fewer, doesn't breach; no-cumulative breaches
3. Flattened rows correctly contain both P-02 and P-03 entries

---

## 4. Document Synchronization Audit

### Consistent ✓
- `spec/algorithm_pseudocode.md` Section 9: shows both `blocked_total` and `blocked_task_total`
- `spec/data_model.md` SchedulerMetrics: includes `blocked_task_total` with correct semantics note
- `spec/scheduler_config.example.json`: 25 keys matching code's 24 SchedulerConfig fields + dry_run
- `qa/validate_scheduler_config.py`: key set matches config, GPU threshold relation check present
- `spec/algorithm_pseudocode.md` Section 8: GPU monitoring correctly describes multi-card worst-case selection

### Gaps Found
- **ISSUE-32** [Low]: `data_model.md` ResourceSnapshot (line 20) missing `gpu_cards: Optional[List[Dict[str, float]]]` field. Code has it at line 30.
- **ISSUE-33** [Low]: `data_model.md` TaskSpec (line 39) missing `target_gpu_index: Optional[int]` field. Code has it at line 41.
- **ISSUE-34** [Low]: `technique_claim_mapping_2026-02-10.md` line number references are stale (e.g., C1 references `:354/:355/:377` but `_evaluate_mode` is now at line 379+). Written before F-14/F-15/F-16 shifted line numbers.

---

## 5. New Issues Found

### ISSUE-32 [Low] `_blocked_task_ids` set grows without bound

- Location: `prototype/resource_scheduler.py:222`, `prototype/resource_scheduler.py:295-297`
- Description: `_blocked_task_ids` is a `Set[str]` that only grows (IDs are added but never removed). In long-running deployments processing millions of unique task IDs, this set will consume increasing memory.
- Comparison: Similar to pre-F-06 event log growth issue. The event log was capped by `max_event_log_entries`; this set has no cap.
- Impact: Low — requires very long runtimes with many unique tasks. Typical batch schedulers reset between sessions.
- Suggested fix: Either add a configurable cap with FIFO eviction, or clear the set periodically (e.g., when scheduler metrics are reset).

### ISSUE-33 [Low] `data_model.md` incomplete field coverage

- Location: `spec/data_model.md:7-20` (ResourceSnapshot), `spec/data_model.md:27-39` (TaskSpec)
- Description: Missing fields:
  - `ResourceSnapshot.gpu_cards: Optional[List[Dict[str, float]]]` (added in F-08)
  - `TaskSpec.target_gpu_index: Optional[int]` (present since GPU multi-card support)
- Impact: Documentation-only. Does not affect code correctness.

### ISSUE-34 [Low] `technique_claim_mapping` stale line references

- Location: `qa/technique_claim_mapping_2026-02-10.md`
- Description: Code line number references (e.g., `resource_scheduler.py:354`) were written before F-14/F-15/F-16 added ~20 lines, shifting all downstream line numbers. References no longer point to the correct code.
- Impact: Audit trail quality reduced. Does not affect functionality.
- Suggested fix: Regenerate line references after code stabilizes, or use anchor comments (e.g., `# [P-02]`) instead of line numbers.

### ISSUE-35 [Low/Observation] No per-task observability during EMERGENCY mode

- Location: `prototype/resource_scheduler.py:268-271`
- Description: In EMERGENCY mode, `start_budget=0` so the admission loop does not execute. Tasks silently pile up in the pending queue without any `TASK_BLOCKED` event being emitted. The `emergency_ticks` metric tracks time in EMERGENCY, but there is no per-task visibility for queued tasks during this period.
- Evidence: In the experiment `emergency` scenario, `blocked_event_total=0` and `blocked_task_total=0` despite 10 tasks being stuck pending for all 10 ticks.
- Impact: Observability gap. In prolonged emergencies, operators cannot see which specific tasks are being held back.
- Suggested fix: Consider emitting a lightweight `TASK_PENDING_DURING_EMERGENCY` event or a periodic pending-queue summary event.

---

## 6. Experiment Output Sanity Check

| Scenario | submitted | started | completed | blocked_events | blocked_tasks | preempted | emergency_ticks | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| normal | 10 | 10 | 10 | 0 | 0 | 0 | 0 | All tasks flow through ✓ |
| high_pressure | 10 | 0 | 0 | 100 | 10 | 0 | 0 | mem=88% → projected breaches emergency, all blocked every tick ✓ |
| emergency | 10 | 0 | 0 | 0 | 0 | 0 | 10 | mem=95% → EMERGENCY, admission loop skipped (ISSUE-35) ✓ |
| burst_then_recover | 10 | 10 | 4 | 18 | 7 | 2 | 6 | Correct burst→preempt→recover cycle ✓ |

The `blocked_task_total == unique_blocked_tasks` cross-validation holds for all scenarios. ✓

---

## 7. Codex Self-Check Reliability Tracking

| Round | Score | Notes |
|---|---|---|
| R3 | 2/10 | Fake fixes (ISSUE-2), fake verification (ISSUE-13) |
| R4 | 8/10 | F-01~F-06 all genuine, but missed BUG-2 |
| R5 | 9/10 | F-07/F-08 genuine, minor doc sync miss |
| R6 | 9/10 | F-09~F-13 genuine, test gaps noted |
| **R7** | **10/10** | **F-14/F-15/F-16 all genuine, math verified, cross-validated** |

Notable improvement: Codex's audit documents (`deep_algorithm_self_audit_R2/R3`) now follow a structured format with reproduction steps, code evidence, and test evidence. The claims are verifiable and accurate.

---

## 8. Overall Assessment

### Strengths
1. **F-14 is high-impact**: GPU guard silently failing on mixed N/A rows was a real production risk. Per-row error handling with `total_mb <= 0` guard is the correct pattern.
2. **F-16 solves the R-04 residual**: The `blocked_total` ambiguity (flagged since R3-supplement as ISSUE-19, tracked as R-04) is now cleanly resolved with dual metrics.
3. **Patent evidence quality**: P-02 and P-03 ablation baselines are well-designed, deterministic, and math-verified. The ablation scheduler subclasses are a clean pattern for comparative testing.
4. **Test coverage**: 32 tests across 2 test files, covering all major code paths including edge cases (N/A GPU rows, threshold validation, blocked metrics deduplication).
5. **Audit document quality**: Self-audit reports are now structured, reproducible, and accurate. A significant improvement from early rounds.

### Remaining Non-Blocking Items
- ISSUE-32: `_blocked_task_ids` unbounded growth (Low)
- ISSUE-33: `data_model.md` missing 2 fields (Low)
- ISSUE-34: Stale claim mapping line numbers (Low)
- ISSUE-35: No per-task observability in EMERGENCY (Low/Observation)
- ISSUE-9: Project direction split (governance — requires user decision)
- ISSUE-13: Prior art fake verification (governance — requires user decision)
- R-05: Multi-GPU no task-level affinity (deferred)

### Judgment

**R7 评审判定：通过（PASS）**

Zero Critical or High defects found. All 3 claimed fixes (F-14/F-15/F-16) verified as genuine with math proofs. 32/32 tests pass. Patent evidence scripts produce correct, reproducible results. 4 new Low-priority issues documented for future improvement.

The resource scheduler codebase is in a mature, well-tested state. The code quality, test coverage, and documentation have improved significantly since R3. The Codex self-check reliability has reached 10/10 for this round.

---

## 9. Recommended Next Steps

1. **Commit current working tree**: 11 files changed, 761 insertions. Recommend a single `feat:` commit covering F-14/F-15/F-16 + patent evidence + experiment updates.
2. **Fix ISSUE-33** (data_model.md field gaps): Quick documentation sync — add `gpu_cards` to ResourceSnapshot and `target_gpu_index` to TaskSpec.
3. **User decision on ISSUE-9**: The `patent/` directory still contains old memory-pipeline patent text. If resource scheduling is the confirmed direction, these documents need rewriting.
4. **Consider ISSUE-32**: Add a configurable cap for `_blocked_task_ids` or periodic reset mechanism.

---

*Review performed by Claude (Opus 4.6) — all assertions independently verified with code reading, math traces, and test execution.*
