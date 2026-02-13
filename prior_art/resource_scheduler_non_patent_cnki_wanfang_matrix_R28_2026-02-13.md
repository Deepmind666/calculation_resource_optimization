# Non-Patent Literature Matrix (CNKI/Wanfang) - R28

- Timestamp: 2026-02-13 16:20:00 +08:00
- Owner: Codex (GPT-5)
- Goal: reduce ISSUE-51 risk by adding traceable non-patent prior-art coverage
- Scope: resource scheduling, task scheduling, resource allocation

## 1. Search Method

Sources:
1. Wanfang literature pages (periodical and thesis records)
2. CNKI official entry pages (for reproducible retrieval route)

Keywords:
1. `GPU resource scheduling`
2. `edge computing task scheduling`
3. `self-scheduling load balancing`
4. `resource allocation algorithm`

Search date: 2026-02-13 (UTC+08:00)

## 2. Literature Matrix (Non-Patent)

| ID | Source | Type | Title | URL | Relevance | Relationship to this project |
|---|---|---|---|---|---|---|
| NP-01 | Wanfang | Periodical | IoT Edge Computing Resource Scheduling and Optimization Strategy | https://d.wanfangdata.com.cn/periodical/fjdn202504008 | High | Directly relevant to dynamic resource scheduling concepts. |
| NP-02 | Wanfang | Thesis | Edge Node Placement and Task Scheduling for Smart Classroom | https://d.wanfangdata.com.cn/thesis/D01544669 | Medium-High | Relevant to task scheduling and resource sharing, but no per-GPU admission loop. |
| NP-03 | Wanfang | Thesis | Study and Application of Self-Scheduling Algorithm in Desktop Grid | https://d.wanfangdata.com.cn/thesis/Y1468732 | Medium | Covers self-scheduling and balancing concepts as background prior art. |
| NP-04 | Wanfang | Thesis | Resource Allocation and Handover Performance under LTE-A Carrier Aggregation | https://d.wanfangdata.com.cn/thesis/Y3125781 | Medium | Resource-allocation algorithm prior art in a different domain. |
| NP-05 | Wanfang | Periodical | PPO-based Job-Shop Scheduling with Convolutional Pyramid Network | https://d.wanfangdata.com.cn/periodical/jxgys202503004 | Medium | Scheduling optimization prior art, different business domain. |
| NP-06 | Chinese Journal Site | Periodical | Multi-Cluster GPU Compute Resource Scheduling Platform with State Awareness | https://www.joconline.com.cn/zh/article/doi/10.11959/j.issn.1000-436x.2025189/ | High | Strongly relevant GPU resource scheduling reference. |

## 3. CNKI Retrieval Route (for archive reproducibility)

1. CNKI periodical entry: https://kns.cnki.net/kns8?dbcode=CJFQ
2. CNKI doctoral thesis entry: https://kns.cnki.net/kns8?dbcode=CDFD
3. CNKI master thesis entry: https://kns.cnki.net/kns8?dbcode=CMFD

Notes:
1. Direct automated extraction from CNKI detail pages is limited in this environment.
2. This round uses Wanfang records as primary machine-verifiable evidence and keeps CNKI route explicit for manual archive follow-up.

## 4. Engineering Difference Conclusion

This round did not find a non-patent source that explicitly discloses the full integrated bundle below as one closed loop:
1. Raw+EMA dual-view mode decision plus same-tick cumulative admission projection.
2. Per-GPU affinity split budgeting (bound/unbound) in same-tick admission accounting.
3. Bottleneck-directed preemption with normalized dual-target reclaim scoring.

Inference:
1. Single techniques have prior-art analogs.
2. The integrated combination still needs formal legal claim-chart defense.

## 5. Remaining Gaps

1. Add CNKI-side archived query-result snapshots (query condition + result page + timestamp).
2. Map NP-06 to code-level features in `qa/technique_claim_mapping_*`.
3. Ask patent counsel to prepare legal obviousness rebuttal for combined feature set.
