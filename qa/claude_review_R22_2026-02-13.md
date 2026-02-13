# Claude Review — R22 (2026-02-13)

## 0. Review Scope

**Codex 轮次**: R29 (evidence archival hardening)
**审查对象**: CNIPA/CNKI snapshot archive + manifest + prior art index/package updates
**Verdict**: **PASS — 工程级证据归档质量可接受，但不推进任何 Critical 专利缺陷**

---

## 1. 测试确认

```
pycache 清理 → OK
python -m unittest discover -s prototype/tests -p "test_*.py"
Ran 75 tests in 0.515s → OK
```

代码基线不变，75/75 通过。R29 无代码/规格/测试变更。

---

## 2. Snapshot 文件完整性验证

### 2.1 CNIPA 证据目录 (5 文件)

| 文件 | Manifest Bytes | 实际 Bytes | SHA256 抽检 | 结论 |
|------|---------------|------------|-------------|------|
| CN117788264A_google_patents.html | 120,307 | 120,307 | **MATCH** (certutil 验证) | OK |
| CN111736987B_google_patents.html | 101,458 | 101,458 | — | OK (size match) |
| CN116719628B_google_patents.html | 119,418 | 119,418 | — | OK (size match) |
| CNIPA_instruction_20230213.html | 2,974 | 2,974 | — | OK (size match) |
| CNIPA_guide_20240401.html | 14,473 | 14,473 | — | OK (size match) |

### 2.2 CNKI 证据目录 (3 + 1 文件)

| 文件 | Manifest Bytes | 实际 Bytes | 结论 |
|------|---------------|------------|------|
| CNKI_CJFQ_entry.html | 26,101 | 26,101 | OK |
| CNKI_CDFD_entry.html | 21,566 | 21,566 | OK |
| CNKI_CMFD_entry.html | 21,566 | 21,566 | OK |
| merge.searchbar.min.js | **未列入 manifest** | 268,073 | **OBS-1**: 未登记的 JS 资源文件 |

### 2.3 失败记录

CNIPA_conventionalSearch → HTTP 412 — 已显式记录在 manifest 中，未做虚假闭环。**诚实标注，合格**。

### 2.4 Manifest JSON 结构

`R29_snapshot_manifest.json` 包含 9 项，每项有 name/url/saved_file/status/http_status/content_type/bytes/sha256/error 字段。结构完整，失败项 sha256=null + saved_file=null 正确。

---

## 3. 实质性评估

### 3.1 R29 实际推进了什么

| 项目 | 状态 |
|------|------|
| 8/9 snapshot 文件落盘且 hash 可验证 | **Done** |
| CNIPA 搜索端点失败已显式记录 | **Done** |
| Prior art index v2 更新引用 R29 | **Done** |
| Package R29 整合文档链 | **Done** |

### 3.2 R29 **未**推进的 R21 Critical 缺陷

| PATENT-ISSUE | 严重度 | R29 进展 |
|-------------|---------|----------|
| PATENT-ISSUE-1: 独立权利要求混入测试方法论 | **Critical** | 未触及 |
| PATENT-ISSUE-2: 权利要求使用代码变量名 | **Critical** | 未触及 |
| PATENT-ISSUE-5: 说明书严重不足 (121 行) | **Critical** | 未触及 |
| PATENT-ISSUE-6: 背景技术无具体引证 | **Critical** | 未触及 |
| PATENT-ISSUE-3: 独立权利要求特征过多 | High | 未触及 |
| PATENT-ISSUE-4: 系统权利要求 15 过简 | High | 未触及 |
| PATENT-ISSUE-7: Prior art 搜索方法缺陷 | High | **微量推进** (snapshot 归档，但未补 Gandiva/OOM Killer 等) |
| PATENT-ISSUE-8: CN-RS-06 定性错误 | High | 未触及 |

### 3.3 CNKI 证据深度评估

三个 CNKI HTML 文件均为**入口页面**（`kns8?dbcode=CJFQ/CDFD/CMFD`），只是数据库首页，不包含任何实际检索查询或结果。这与 R21 §4.4 的发现一致：当前 CNKI 证据仍为**路由级**，不具备检索结果可复现性。

---

## 4. Issues

### OBS-1 (Info) — CNKI 目录包含未登记的 JS 文件

`prior_art/evidence/cnki_route_R29_2026-02-13/merge.searchbar.min.js` (268,073 bytes) 未出现在 manifest 中。看起来是 CNKI 页面自动加载的 JavaScript 资源。应从证据目录移除或追加到 manifest。

### OBS-2 (Info) — CNKI 证据仍为入口页

3 个 CNKI HTML 仅证明"可以访问 CNKI 入口"，不证明"执行了关键词检索并获取结果"。对于 prior art 搜索合规性，这不构成有效检索证据。

---

## 5. Overall Assessment

**PASS** — R29 在工程层面完成了 snapshot 归档任务，质量可接受：
- 8/9 文件成功抓取，hash 可验证（抽检 1 项 SHA256 完全匹配）
- 1 项失败显式记录，未虚假闭环
- Manifest JSON 结构完整
- Codex 自查报告准确（无夸大）

**但必须强调**：R29 是一个**收尾性归档轮次**，对专利提交就绪度的推进几乎为零。**4 个 Critical 缺陷 (PATENT-ISSUE-1/2/5/6) 和 4 个 High 缺陷 (PATENT-ISSUE-3/4/7/8) 仍然全部 OPEN**。

**下一步优先级不变**（与 R21 一致）：
1. 修复 PATENT-ISSUE-1/2/5/6 (4 Critical) — 权利要求重构 + 说明书扩写
2. 补充 Gandiva/Tiresias/AntMan/Pollux/Linux OOM Killer 覆盖 (PATENT-ISSUE-7)
3. 修正 CN-RS-06 定性 (PATENT-ISSUE-8)

---

*Reviewed by Claude Opus 4.6 — 2026-02-13*
