# CNIPA + CNKI Snapshot Archive Report - R30

- Timestamp: 2026-02-13 18:20:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: extend snapshot archive with CNKI result-page captures and reproducible manifest
- Evidence root: `prior_art/evidence/`

## 1. Capture Summary

1. Total targets: 14
2. Successful captures: 13
3. Failed captures: 1
4. Manifest: `prior_art/evidence/R30_snapshot_manifest.json`

## 2. Successful Captures (with hash)

| Name | URL | HTTP | Bytes | SHA256 | Saved File |
|---|---|---:|---:|---|---|
| CN117788264A_google_patents | https://patents.google.com/patent/CN117788264A/en | 200 | 120307 | `0cf5b61cdc8d7f53875c66b049b9b958fcc126ef8b9b1bcfec4337dc726d90de` | `prior_art/evidence/cnipa_status_R30_2026-02-13/CN117788264A_google_patents.html` |
| CN111736987B_google_patents | https://patents.google.com/patent/CN111736987B/zh | 200 | 101458 | `210993148fe0289b1f942938b25cbb59d8de45d90ffb5000e71984d70277d954` | `prior_art/evidence/cnipa_status_R30_2026-02-13/CN111736987B_google_patents.html` |
| CN116719628B_google_patents | https://patents.google.com/patent/CN116719628B/zh | 200 | 119418 | `e8b8f0070919ba912f58990893c5a9e34d3a2d40d50193a262fc9cce11686ba0` | `prior_art/evidence/cnipa_status_R30_2026-02-13/CN116719628B_google_patents.html` |
| CNIPA_instruction_20230213 | https://www.cnipa.gov.cn/art/2023/2/13/art_3166_182074.html | 200 | 10502 | `dc120d1113d23f346fcb15eda9c2989c4f7dbf37b6f5d930b8d4077fc8e73bdb` | `prior_art/evidence/cnipa_status_R30_2026-02-13/CNIPA_instruction_20230213.html` |
| CNIPA_guide_20240401 | https://www.cnipa.gov.cn/art/2024/4/1/art_3359_191346.html | 200 | 14473 | `e20715afbd7dbd28af303429d19386b51a16d2a27ec2aec2d2eb225bf8236380` | `prior_art/evidence/cnipa_status_R30_2026-02-13/CNIPA_guide_20240401.html` |
| CNKI_CJFQ_entry | https://kns.cnki.net/kns8?dbcode=CJFQ | 200 | 26177 | `0f0610c919010c2b04fd2474587ce127666995d068285d63e9d93f16ee7e1047` | `prior_art/evidence/cnki_route_R30_2026-02-13/CNKI_CJFQ_entry.html` |
| CNKI_CDFD_entry | https://kns.cnki.net/kns8?dbcode=CDFD | 200 | 21566 | `b8863f6b4846f6939a6aa3ffa2b095f8d606c2986139604ff81083c37eee9452` | `prior_art/evidence/cnki_route_R30_2026-02-13/CNKI_CDFD_entry.html` |
| CNKI_CMFD_entry | https://kns.cnki.net/kns8?dbcode=CMFD | 200 | 21570 | `5ee92fbdbaa5d3bd4d1794b9aec9c9c74996f1256430e127eaa5c7f99169c9cf` | `prior_art/evidence/cnki_route_R30_2026-02-13/CNKI_CMFD_entry.html` |
| CNKI_AdvSearch | https://kns.cnki.net/kns8/AdvSearch | 200 | 50056 | `073feec0c55abd6a6b6eff215ee631e35ce60176c0190effe0eb5101b87cb20b` | `prior_art/evidence/cnki_result_R30_2026-02-13/CNKI_AdvSearch.html` |
| CNKI_defaultresult_empty | https://kns.cnki.net/kns8/defaultresult/index | 200 | 26810 | `1eb1da8987cc14f3e19f1fa12c4effe7efacc47e6fc1d89c9ad41c9036c13f22` | `prior_art/evidence/cnki_result_R30_2026-02-13/CNKI_defaultresult_empty.html` |
| CNKI_defaultresult_kw_1 | https://kns.cnki.net/kns8/defaultresult/index?kw=GPU%20%3F%3F%20%3F%3F | 200 | 26810 | `1eb1da8987cc14f3e19f1fa12c4effe7efacc47e6fc1d89c9ad41c9036c13f22` | `prior_art/evidence/cnki_result_R30_2026-02-13/CNKI_defaultresult_kw_1.html` |
| CNKI_defaultresult_kw_2 | https://kns.cnki.net/kns8/defaultresult/index?kw=%3F%3F%3F%3F%20%3F%3F%20%3F%3F | 200 | 26810 | `1eb1da8987cc14f3e19f1fa12c4effe7efacc47e6fc1d89c9ad41c9036c13f22` | `prior_art/evidence/cnki_result_R30_2026-02-13/CNKI_defaultresult_kw_2.html` |
| CNKI_defaultresult_kw_3 | https://kns.cnki.net/kns8/defaultresult/index?kw=%3F%3F%3F%20%3F%3F%3F%3F | 200 | 26810 | `1eb1da8987cc14f3e19f1fa12c4effe7efacc47e6fc1d89c9ad41c9036c13f22` | `prior_art/evidence/cnki_result_R30_2026-02-13/CNKI_defaultresult_kw_3.html` |

## 3. Failed Captures

| Name | URL | HTTP | Error | Error Body |
|---|---|---:|---|---|
| CNIPA_conventionalSearch | https://pss-system.cponline.cnipa.gov.cn/conventionalSearch | 412 | HTTPError 412: Precondition Failed | `prior_art/evidence/cnipa_status_R30_2026-02-13/CNIPA_conventionalSearch.error.html` |

## 4. What R30 Adds Beyond R29

1. Added CNKI result-page route captures under `cnki_result_R30_2026-02-13/`.
2. Added per-request header snapshots (`*.headers.txt`) for all targets.
3. Captured HTTP 412 error body for CNIPA search endpoint as explicit evidence.

## 5. Interpretation and Limits

1. CN-RS-01/04/06 source pages remain archived with hash and size verification.
2. CNKI route and result-page URLs are archived at engineering evidence level.
3. CNIPA search endpoint still blocks scripted access (HTTP 412) and needs manual screenshot/export for legal filing package.
4. This report is engineering evidence, not a legal opinion.

## 6. Archive File List (R30)

1. `prior_art/evidence/R30_targets.json`
2. `prior_art/evidence/R30_snapshot_manifest.json`
3. `prior_art/evidence/cnipa_status_R30_2026-02-13/`
4. `prior_art/evidence/cnki_route_R30_2026-02-13/`
5. `prior_art/evidence/cnki_result_R30_2026-02-13/`
6. `qa/archive_web_snapshots.py`
