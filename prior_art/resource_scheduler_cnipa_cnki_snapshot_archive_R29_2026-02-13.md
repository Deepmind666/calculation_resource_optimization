# CNIPA + CNKI Snapshot Archive Report - R29

- Timestamp: 2026-02-13 17:05:00 +08:00
- Owner: Codex (GPT-5)
- Purpose: attach machine-verifiable archive evidence for legal-status and retrieval-route checks
- Evidence root: `prior_art/evidence/`

## 1. Capture Summary

1. Total targets: 9
2. Successful captures: 8
3. Failed captures: 1

## 2. Successful Captures (with hash)

| Name | URL | HTTP | Bytes | SHA256 | Saved File |
|---|---|---:|---:|---|---|
| CN117788264A_google_patents | https://patents.google.com/patent/CN117788264A/en | 200 | 120307 | `0cf5b61cdc8d7f53875c66b049b9b958fcc126ef8b9b1bcfec4337dc726d90de` | `prior_art/evidence/cnipa_status_R29_2026-02-13/CN117788264A_google_patents.html` |
| CN111736987B_google_patents | https://patents.google.com/patent/CN111736987B/zh | 200 | 101458 | `210993148fe0289b1f942938b25cbb59d8de45d90ffb5000e71984d70277d954` | `prior_art/evidence/cnipa_status_R29_2026-02-13/CN111736987B_google_patents.html` |
| CN116719628B_google_patents | https://patents.google.com/patent/CN116719628B/zh | 200 | 119418 | `e8b8f0070919ba912f58990893c5a9e34d3a2d40d50193a262fc9cce11686ba0` | `prior_art/evidence/cnipa_status_R29_2026-02-13/CN116719628B_google_patents.html` |
| CNIPA_instruction_20230213 | https://www.cnipa.gov.cn/art/2023/2/13/art_3166_182074.html | 200 | 2974 | `d2ccae26b64f4be039a5fdca9b3f577f456a0e575e87253bcd67fd02d7f70bd7` | `prior_art/evidence/cnipa_status_R29_2026-02-13/CNIPA_instruction_20230213.html` |
| CNIPA_guide_20240401 | https://www.cnipa.gov.cn/art/2024/4/1/art_3359_191346.html | 200 | 14473 | `e20715afbd7dbd28af303429d19386b51a16d2a27ec2aec2d2eb225bf8236380` | `prior_art/evidence/cnipa_status_R29_2026-02-13/CNIPA_guide_20240401.html` |
| CNKI_CJFQ_entry | https://kns.cnki.net/kns8?dbcode=CJFQ | 200 | 26101 | `e49f73caac33466e1bdcd8368714a5263cacaeaa1c254d44a577bf71e22ccc8d` | `prior_art/evidence/cnki_route_R29_2026-02-13/CNKI_CJFQ_entry.html` |
| CNKI_CDFD_entry | https://kns.cnki.net/kns8?dbcode=CDFD | 200 | 21566 | `b8863f6b4846f6939a6aa3ffa2b095f8d606c2986139604ff81083c37eee9452` | `prior_art/evidence/cnki_route_R29_2026-02-13/CNKI_CDFD_entry.html` |
| CNKI_CMFD_entry | https://kns.cnki.net/kns8?dbcode=CMFD | 200 | 21566 | `47c2710507775c61ea098a5e87f30228ab879eafe0abed9ce42ed63fc9372b75` | `prior_art/evidence/cnki_route_R29_2026-02-13/CNKI_CMFD_entry.html` |

## 3. Failed Captures

| Name | URL | HTTP | Error |
|---|---|---:|---|
| CNIPA_conventionalSearch | https://pss-system.cponline.cnipa.gov.cn/conventionalSearch | 412 | HTTPError 412: Precondition Failed |

## 4. Interpretation and Limits

1. CN Google Patents pages for CN-RS-01/04/06 were archived successfully with hashes and byte counts.
2. CNIPA instruction/guide pages were archived successfully.
3. CNIPA search portal endpoint returned HTTP 412 in this scripted capture path; this is recorded as a verifiable failure, not hidden.
4. CNKI entry pages (CJFQ/CDFD/CMFD) were archived successfully as route-level evidence.
5. This archive is engineering-grade evidence; legal filing still needs official screenshot/export package where required.

## 5. Archive File List

1. `prior_art/evidence/R29_snapshot_manifest.json`
2. `prior_art/evidence/cnipa_status_R29_2026-02-13/snapshot_summary.md`
3. `prior_art/evidence/cnki_route_R29_2026-02-13/snapshot_summary.md`
4. `prior_art/evidence/cnipa_status_R29_2026-02-13/*.html`
5. `prior_art/evidence/cnki_route_R29_2026-02-13/*.html`
