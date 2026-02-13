# Resource Scheduler Prior-Art Package (R30)

- Timestamp: 2026-02-13 18:28:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: consolidated handoff package after automated snapshot archiving and CNKI result-page capture

## 1. Read Order

1. `prior_art/resource_scheduler_prior_art_index_v2_2026-02-13.md`
2. `prior_art/resource_scheduler_claim_level_RS-P01_v2_2026-02-13.md`
3. `prior_art/resource_scheduler_claim_level_CN_top3_2026-02-13.md`
4. `prior_art/resource_scheduler_non_patent_cnki_wanfang_matrix_R28_2026-02-13.md`
5. `prior_art/resource_scheduler_cnipa_search_log_2026-02-13.md`
6. `prior_art/resource_scheduler_cnipa_legal_status_appendix_2026-02-13.md`
7. `prior_art/resource_scheduler_cnipa_legal_status_archive_R28_2026-02-13.md`
8. `prior_art/resource_scheduler_cnipa_cnki_snapshot_archive_R30_2026-02-13.md`
9. `prior_art/evidence/R30_snapshot_manifest.json`
10. `qa/technique_claim_mapping_resource_scheduler_v2_2026-02-13.md`

## 2. New in R30

1. Added reusable snapshot script: `qa/archive_web_snapshots.py`.
2. Added target config: `prior_art/evidence/R30_targets.json`.
3. Added CNKI result-page captures under `cnki_result_R30_2026-02-13/`.
4. Added per-request headers and hash manifest for all captured targets.
5. Added explicit error-body archive for CNIPA 412 response.

## 3. Current Closure View

Substantially closed (engineering level):
1. RS-P01 claim-level risk baseline.
2. CN top-3 claim-level engineering comparison.
3. CN/Wanfang non-patent matrix (first pass).
4. CN legal-status engineering archive.
5. Snapshot artifacts with hashes and response headers.
6. CNKI result-page route-level snapshots.

Not fully closed (legal filing level):
1. CNIPA official screenshot/export package accepted by legal process.
2. CNKI detailed result record exports accepted by legal process.
3. Counsel-reviewed legal claim charts.

## 4. Reviewer Quick Checks

1. Verify `R30_snapshot_manifest.json` hashes against archived files.
2. Confirm CNIPA 412 failure is explicitly preserved (not hidden).
3. Confirm CNKI result-page snapshots exist in `cnki_result_R30_2026-02-13/`.
4. Confirm unresolved legal-grade items remain explicit.
