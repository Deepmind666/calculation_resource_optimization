# Resource Scheduler Search Method Upgrade (R32)

- Timestamp: 2026-02-13 20:38:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: narrow PATENT-ISSUE-7 by documenting broader, reviewable search methodology

## 1. Search Scope Expansion

Compared with earlier rounds, this upgrade explicitly includes:
1. CN patent candidates (CNIPA pathway + mirrored public patent pages).
2. Global patent family risk (US20200167197A1 family).
3. Framework baselines (Kubernetes, Slurm, YARN).
4. Kernel-level mechanisms (Linux OOM/PSI/cgroup).
5. GPU scheduler literature (Gandiva, Tiresias, AntMan, Pollux).

## 2. Classification and Query Strategy

Primary classes and themes:
1. G06F 9/50 (scheduling and resource assignment related themes).
2. G06F 11/34 and related fault/pressure handling themes.
3. Query themes:
   - admission control
   - resource projection
   - GPU affinity scheduling
   - preemptive reclaim
   - pressure-triggered eviction
   - smoothed vs raw telemetry decision

## 3. Sources Used

1. Patent pages (Google Patents links for CN/US families).
2. Official framework docs (kubernetes.io, slurm.schedmd.com, hadoop.apache.org).
3. Kernel docs (docs.kernel.org).
4. USENIX publication pages for OSDI/NSDI scheduler papers.

## 4. Quality Rules Applied

1. Every row in the global matrix has a direct URL.
2. Risk rating is tied to claim-core overlap, not title similarity.
3. Domain mismatch is explicitly downgraded (example: CN116719628B).
4. Open legal-grade gaps are retained explicitly (no fake closure).

## 5. Explicit Corrections in This Round

1. CN116719628B risk reclassified to Low in claim-level CN top3 chart due to domain mismatch:
   - transmission-link concurrent dispatch vs compute-resource admission/reclaim.
2. Global non-patent scheduler matrix added to cover missing English baselines:
   - `resource_scheduler_non_patent_global_matrix_R32_2026-02-13.md`

## 6. Remaining Gaps (Still Open)

1. Counsel-grade legal claim construction is still required for filing.
2. CNIPA interactive official export remains partially blocked in scripted capture path.
3. CNKI result pages remain route-level evidence in this environment and should be complemented by manual screenshot capture for legal package completeness.

## 7. Output References

1. `prior_art/resource_scheduler_prior_art_index_v2_2026-02-13.md`
2. `prior_art/resource_scheduler_claim_level_CN_top3_2026-02-13.md`
3. `prior_art/resource_scheduler_non_patent_global_matrix_R32_2026-02-13.md`
4. `prior_art/resource_scheduler_cnipa_cnki_snapshot_archive_R30_2026-02-13.md`
