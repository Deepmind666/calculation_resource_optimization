# Claude Review — R23 (2026-02-13)

## 0. Review Scope

**Codex 轮次**: R30 (snapshot pipeline upgrade + CNKI result-page capture)
**审查对象**: Reusable archiver tool, R30 manifest, CNKI result-page captures, package/index updates
**Verdict**: **Conditional PASS — CNKI 关键词检索编码损坏，须修复后方可声称已执行 CNKI 检索**

---

## 1. 测试确认

```
pycache 清理 → OK
python -m unittest discover -s prototype/tests -p "test_*.py"
Ran 75 tests in 0.493s → OK
```

代码基线不变。R30 无调度器代码/规格/测试变更。

---

## 2. R30 新增内容评估

### 2.1 Reusable Archiver Tool

新增 `qa/archive_web_snapshots.py`，支持 target JSON → manifest JSON 流水线。架构改善合理。

### 2.2 CNIPA 证据 (与 R29 一致)

| 项目 | 状态 | 备注 |
|------|------|------|
| 3 × Google Patents HTML | OK | SHA256 与 R29 一致（同页面） |
| CNIPA instruction/guide | OK | CNIPA_instruction bytes 从 R29 的 2,974 变为 10,502（页面更新正常） |
| CNIPA_conventionalSearch | HTTP 412 | **改善**: R30 保存了 error body (2,451 bytes + SHA256) 而非仅记录失败 |

### 2.3 CNKI 入口页 (与 R29 基本一致)

3 个数据库入口页正常存档。

---

## 3. ISSUE-64 (High) — CNKI 关键词检索编码损坏

**这是本轮最重要的发现。**

### 3.1 证据

R30_targets.json 中三个关键词搜索的 URL：
```
kw=GPU%20%3F%3F%20%3F%3F
kw=%3F%3F%3F%3F%20%3F%3F%20%3F%3F
kw=%3F%3F%3F%20%3F%3F%3F%3F
```

`%3F` = URL-encoded `?`（问号）。中文关键词被损坏为 `?` 后再被 URL 编码。

### 3.2 `cnki_query_conditions.txt` 自相矛盾

该文件同时包含：
- **正确的 URL**（行 8-10）：`kw=GPU%20%E8%B5%84%E6%BA%90%20%E8%B0%83%E5%BA%A6` = `GPU 资源 调度`
- **损坏的关键词**（行 12-14）：`GPU ?? ??`

说明 Codex **知道**正确的编码，但 targets.json 中写入了损坏版本。

### 3.3 结果

四个 "搜索结果" 页面（empty + kw_1 + kw_2 + kw_3）：
- **完全相同的 SHA256**: `1eb1da8987cc14f3e19f1fa12c4effe7efacc47e6fc1d89c9ad41c9036c13f22`
- **完全相同的字节数**: 26,810

这证明 CNKI 对所有损坏的关键词返回了同一个**空白默认页面**。没有执行任何有效的关键词检索。

### 3.4 影响

当前 CNKI "搜索结果" 证据**完全无效**。比没有更糟——它制造了一种"已执行检索"的假象。

### 3.5 修复方案

R30_targets.json 中关键词 URL 应使用 `cnki_query_conditions.txt` 行 8-10 中的正确编码：
```json
"url": "https://kns.cnki.net/kns8/defaultresult/index?kw=GPU%20%E8%B5%84%E6%BA%90%20%E8%B0%83%E5%BA%A6"
"url": "https://kns.cnki.net/kns8/defaultresult/index?kw=%E8%BE%B9%E7%BC%98%E8%AE%A1%E7%AE%97%20%E4%BB%BB%E5%8A%A1%20%E8%B0%83%E5%BA%A6"
"url": "https://kns.cnki.net/kns8/defaultresult/index?kw=%E8%87%AA%E8%B0%83%E5%BA%A6%20%E8%B4%9F%E8%BD%BD%E5%9D%87%E8%A1%A1"
```

注意：即使修复编码，CNKI 搜索可能仍需要 JavaScript 执行/登录态，scripted GET 可能依然返回空页面。

---

## 4. Issue Status

| ID | Severity | 状态 | 说明 |
|----|----------|------|------|
| PATENT-ISSUE-1 | **Critical** | OPEN | 独立权利要求混入测试方法论 |
| PATENT-ISSUE-2 | **Critical** | OPEN | 权利要求使用代码变量名 |
| PATENT-ISSUE-5 | **Critical** | OPEN | 说明书严重不足 |
| PATENT-ISSUE-6 | **Critical** | OPEN | 背景技术无具体引证 |
| PATENT-ISSUE-3 | High | OPEN | 独立权利要求特征过多 |
| PATENT-ISSUE-4 | High | OPEN | 系统权利要求 15 过简 |
| PATENT-ISSUE-7 | High | OPEN | Prior art 搜索方法缺陷 |
| PATENT-ISSUE-8 | High | OPEN | CN-RS-06 定性错误 |
| **ISSUE-64** | **High** | **NEW** | CNKI 关键词编码损坏，搜索结果全部无效 |
| OBS-1 | Info | R29→R30 修复 | R29 的未登记 JS 文件问题在 R30 未复现 |
| OBS-2 | Info | OPEN | CNKI 证据仍为路由级 |

---

## 5. Overall Assessment

**Conditional PASS** — R30 在工程管线层面有实质改善（reusable archiver、error body 归档、header 保存），但 CNKI 关键词检索因编码损坏**完全失败**。

**R30 实际推进**：
- Reusable snapshot pipeline（质量改善）
- CNIPA 412 error body 归档（比 R29 进步）
- 14 targets 结构化管理

**R30 未推进**：
- 4 Critical + 4 High 专利文本缺陷全部 OPEN
- CNKI 检索仍无有效证据（ISSUE-64 使 R30 的 CNKI result 部分无效）

**建议**：停止继续投入 prior art 归档基础设施。当前阻塞项是**专利文本质量**（PATENT-ISSUE-1/2/5/6），不是证据归档格式。

---

*Reviewed by Claude Opus 4.6 — 2026-02-13*
