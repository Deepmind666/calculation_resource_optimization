# 九步流程伪代码（v0.1）

更新时间：2026-02-09（UTC+08:00）

## 全流程入口

```text
INPUT:
  fragments_stream
  retention_contract
  global_token_budget B

OUTPUT:
  cluster_memory_units
  allocation_plan
  audit_report

for each fragment in fragments_stream:
    f <- collect_and_annotate(fragment)                      # Step 1
    candidates <- coarse_retrieval(f.embedding)              # Step 2
    decision <- precise_cluster_decision(f, candidates)      # Step 3
    apply_cluster_update(decision)

for each cluster in active_clusters:
    consensus, evidence, credit <- redundancy_arbitration(cluster)      # Step 4
    conflicts <- conflict_detection(cluster)                             # Step 5
    draft <- contract_guided_summary(cluster, retention_contract)        # Step 6
    final <- fidelity_check_and_rewrite(draft, cluster, retention_contract) # Step 7
    save_cluster_memory_unit(cluster, consensus, conflicts, evidence, final)

allocation_plan <- token_budget_optimization(active_clusters, B)         # Step 8
build_hierarchical_index_and_trace(active_clusters)                      # Step 9
audit_report <- emit_audit_report(active_clusters, allocation_plan)
return cluster_memory_units, allocation_plan, audit_report
```

## Step 1 碎片采集与标注

```text
function collect_and_annotate(fragment):
    fragment.fragment_id <- uuid()
    fragment.timestamp <- now()
    fragment.tool_fingerprint <- hash(tool_outputs)
    fragment.topic_candidates <- topic_predict(fragment.content)
    fragment.confidence <- init_confidence(fragment.source_agent)
    fragment.trace_pointer <- store_raw_input_and_get_pointer(fragment.raw)
    fragment.embedding <- embed(fragment.content)
    return fragment
```

## Step 2 候选近邻检索（粗筛）

```text
function coarse_retrieval(embedding):
    c1 <- ann_index.search(embedding, top_k)
    c2 <- lsh_index.search(embedding, top_k)
    return deduplicate(c1 ∪ c2)
```

## Step 3 精判并簇/新簇/拆簇

```text
function precise_cluster_decision(f, candidates):
    best_score <- -inf
    best_cluster <- null
    for c in candidates:
        s_sem <- semantic_similarity(f.embedding, c.centroid)
        s_topic <- topic_consistency(f.topic_candidates, c.topic_distribution)
        s_src <- source_reliability(f.source_agent, c)
        s_conflict <- conflict_risk_penalty(f, c)
        score <- w1*s_sem + w2*s_topic + w3*s_src - w4*s_conflict
        if score > best_score:
            best_score <- score
            best_cluster <- c
    if best_score < tau_new:
        return NEW_CLUSTER
    if split_condition(best_cluster):
        return SPLIT_CLUSTER(best_cluster)
    return MERGE(best_cluster)
```

## Step 4 跨智能体冗余仲裁

```text
function redundancy_arbitration(cluster):
    statements <- extract_statements(cluster.fragments)
    for st in statements:
        st.credit <- alpha*source_confidence(st.source_agent)
                    + beta*citation_frequency(st)
                    + gamma*tool_consistency(st)
    consensus <- select_top_statements(statements, policy="coverage+confidence")
    evidence <- collect_evidence_pointers(consensus)
    return consensus, evidence, statements
```

## Step 5 冲突检测与分叉

```text
function conflict_detection(cluster):
    conflicts <- []
    for (a, b) in pairwise(cluster.statements):
        if contradiction(a, b):       # NLI 或规则分类器
            conflicts.append({A:a, B:b, evidence:[a.id, b.id]})
    return conflicts
```

## Step 6 契约驱动摘要生成

```text
function contract_guided_summary(cluster, contract):
    required_slots <- contract.required_slots
    summary <- generate_summary_with_slots(cluster, required_slots)
    slot_coverage <- compute_slot_coverage(summary, required_slots)
    return {summary: summary, slot_coverage: slot_coverage}
```

## Step 7 证明式保真校验与重写

```text
function fidelity_check_and_rewrite(draft, cluster, contract):
    for i in range(contract.max_rounds):
        must_keep <- extract_must_keep_facts(cluster, contract)
        ok_entail <- entailment_check(draft.summary, must_keep)
        ok_conflict <- no_new_unsupported_claim(draft.summary, cluster.evidence)
        ok_slots <- slot_coverage_pass(draft.slot_coverage, contract)
        if ok_entail and ok_conflict and ok_slots:
            return draft
        draft <- rewrite_with_feedback(draft, must_keep, cluster.evidence, contract)
    return fallback_conservative_summary(cluster.evidence)
```

## Step 8 全局 token 预算优化

```text
function token_budget_optimization(clusters, B):
    # maximize Σ Ui(li), s.t. Σ li <= B, li >= lmin_i
    initialize li <- lmin_i
    remain <- B - Σ li
    while remain > 0:
        i <- argmax marginal_gain(Ui, li)
        li <- li + delta
        remain <- remain - delta
    return {cluster_i: li}
```

## Step 9 分层索引与可追溯恢复

```text
function build_hierarchical_index_and_trace(clusters):
    for c in clusters:
        index_level0.store(c.cluster_id, c.summary)
        index_level1.store(c.cluster_id, c.evidence_pointers)
        for eid in c.evidence_pointers:
            trace_map[c.cluster_id].append(eid)
```

## 审计报告输出结构

```json
{
  "cluster_id": "C-001",
  "slot_coverage": {"facts": 1.0, "procedure-steps": 0.8},
  "evidence_ids": ["F-1001", "F-1023"],
  "conflict_branches": [{"A": "x", "B": "y"}],
  "rewrite_history": [{"round": 1, "reason": "slot missing"}]
}
```
