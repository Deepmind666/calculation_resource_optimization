"""
专利文档 PDF 生成脚本
将 markdown 专利文档按 CNIPA 顺序拼合为 A4 PDF。
依赖: pip install markdown pymupdf
"""

import sys
import os
import re
import markdown
import fitz  # PyMuPDF


# ── 配置 ──────────────────────────────────────────────
PATENT_DIR = os.path.join(os.path.dirname(__file__), "..", "patent")

SECTIONS = [
    {
        "title": "摘  要",
        "file": "摘要_资源调度_CNIPA_独立页_R44.md",
        "page_break": True,
    },
    {
        "title": "权 利 要 求 书",
        "file": "权利要求书_资源调度_CNIPA_修正版_R44.md",
        "page_break": True,
    },
    {
        "title": "说  明  书",
        "file": "说明书_资源调度_CNIPA_完整稿_R44.md",
        "page_break": True,
    },
    {
        "title": "附 图 说 明",
        "file": "附图文字描述稿_CNIPA_R43.md",
        "page_break": True,
    },
    {
        "title": "附 图 标 记 说 明 表",
        "file": "附图标记说明表_资源调度_CNIPA_R44_核验版.md",
        "page_break": True,
    },
]

# SVG 附图
SVG_FILES = [
    ("附图 1：系统模块结构", "附图_资源调度_图1_系统模块.svg"),
    ("附图 2：调度周期流程", "附图_资源调度_图2_调度周期流程.svg"),
    ("附图 3：三模式对比", "附图_资源调度_图3_真机三模式对比.svg"),
    ("附图 4：自适应调优轨迹", "附图_资源调度_图4_自适应重试轨迹.svg"),
]

OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "patent", "专利申请文件_初稿.pdf"
)

# ── CSS 样式 ──────────────────────────────────────────
CSS = """
body {
    font-family: "SimSun", "宋体", "Noto Serif CJK SC", serif;
    font-size: 12pt;
    line-height: 1.8;
    color: #000;
}
h1 {
    font-family: "SimHei", "黑体", "Noto Sans CJK SC", sans-serif;
    font-size: 18pt;
    text-align: center;
    margin-top: 20pt;
    margin-bottom: 16pt;
    page-break-before: always;
}
h1:first-child {
    page-break-before: avoid;
}
h2 {
    font-family: "SimHei", "黑体", "Noto Sans CJK SC", sans-serif;
    font-size: 14pt;
    margin-top: 14pt;
    margin-bottom: 8pt;
}
h3 {
    font-family: "SimHei", "黑体", "Noto Sans CJK SC", sans-serif;
    font-size: 12pt;
    margin-top: 10pt;
    margin-bottom: 6pt;
}
h4 {
    font-family: "SimHei", "黑体", "Noto Sans CJK SC", sans-serif;
    font-size: 12pt;
    margin-top: 8pt;
    margin-bottom: 4pt;
}
p {
    text-indent: 2em;
    margin: 4pt 0;
}
li {
    margin: 2pt 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 8pt 0;
    font-size: 10pt;
}
th, td {
    border: 1px solid #000;
    padding: 4pt 6pt;
    text-align: left;
}
th {
    font-family: "SimHei", "黑体", sans-serif;
    background-color: #f0f0f0;
}
code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 10pt;
    background-color: #f5f5f5;
    padding: 1pt 3pt;
}
pre {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 9pt;
    background-color: #f5f5f5;
    padding: 6pt;
    border: 1px solid #ccc;
    white-space: pre-wrap;
    word-wrap: break-word;
}
hr {
    border: none;
    border-top: 1px solid #999;
    margin: 12pt 0;
}
.section-title {
    font-family: "SimHei", "黑体", sans-serif;
    font-size: 22pt;
    text-align: center;
    margin-top: 40pt;
    margin-bottom: 30pt;
    letter-spacing: 4pt;
}
.cover-title {
    font-family: "SimHei", "黑体", sans-serif;
    font-size: 28pt;
    text-align: center;
    margin-top: 120pt;
    margin-bottom: 20pt;
}
.cover-subtitle {
    font-family: "SimSun", "宋体", serif;
    font-size: 16pt;
    text-align: center;
    margin-bottom: 8pt;
    color: #333;
}
"""


def read_md(filepath: str) -> str:
    """Read markdown file and return content without YAML-like header."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    # Strip leading markdown title if it's a metadata header (# 权利要求书(...))
    # Keep the content
    return text


def md_to_html(md_text: str) -> str:
    """Convert markdown text to HTML."""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br"],
    )


def clean_md_header(md_text: str) -> str:
    """Remove the first H1 line and metadata lines (timestamps, etc.)."""
    lines = md_text.split("\n")
    cleaned = []
    skip_header = True
    for line in lines:
        if skip_header:
            # Skip lines that are: H1, empty, or metadata (- 时间戳/编制人/版本/用途)
            stripped = line.strip()
            if stripped.startswith("# "):
                continue
            if stripped == "":
                continue
            if stripped.startswith("- 时间戳") or stripped.startswith("- 编制人"):
                continue
            if stripped.startswith("- 版本") or stripped.startswith("- 用途"):
                continue
            if stripped.startswith("- 说明"):
                continue
            if stripped.startswith("- 核查"):
                continue
            if stripped.startswith("- 适用"):
                continue
            skip_header = False
        cleaned.append(line)
    return "\n".join(cleaned)


def build_cover_html() -> str:
    """Build cover page HTML."""
    return """
    <div class="cover-title">发 明 专 利 申 请</div>
    <div class="cover-subtitle">（初稿 · 内部评审用）</div>
    <div class="cover-subtitle">&nbsp;</div>
    <div class="cover-subtitle">发明名称：一种多资源动态调度方法、系统及存储介质</div>
    <div class="cover-subtitle">&nbsp;</div>
    <div class="cover-subtitle">申请人：（待填）</div>
    <div class="cover-subtitle">发明人：（待填）</div>
    <div class="cover-subtitle">&nbsp;</div>
    <div class="cover-subtitle">编制日期：2026-02-14</div>
    """


def build_full_html() -> str:
    """Build complete HTML document."""
    parts = []

    # Cover page
    parts.append(build_cover_html())

    # Each section
    for sec in SECTIONS:
        filepath = os.path.join(PATENT_DIR, sec["file"])
        if not os.path.exists(filepath):
            print(f"  [WARN] 文件不存在，跳过: {sec['file']}")
            continue

        md_text = read_md(filepath)
        md_text = clean_md_header(md_text)

        # Section title
        parts.append(f'<h1 class="section-title">{sec["title"]}</h1>')

        # Convert MD to HTML
        html_body = md_to_html(md_text)
        parts.append(html_body)

    # SVG figures section
    parts.append('<h1 class="section-title">附  图</h1>')
    for fig_title, svg_name in SVG_FILES:
        svg_path = os.path.join(PATENT_DIR, svg_name)
        if os.path.exists(svg_path):
            parts.append(f"<h2>{fig_title}</h2>")
            parts.append(f"<p style='text-indent:0;text-align:center;color:#666;'>"
                         f"（见附件 SVG 文件：{svg_name}）</p>")
        else:
            parts.append(f"<h2>{fig_title}</h2>")
            parts.append(f"<p style='text-indent:0;color:red;'>文件缺失: {svg_name}</p>")

    full_html = "\n".join(parts)
    return full_html


def render_pdf(html_content: str, css: str, output_path: str):
    """Use PyMuPDF Story to render HTML+CSS to PDF."""
    story = fitz.Story(html_content, user_css=css)

    # A4 page: 595 x 842 points
    page_width = 595
    page_height = 842
    margin_top = 72      # 1 inch = 72pt
    margin_bottom = 72
    margin_left = 72
    margin_right = 54    # CNIPA 右侧可稍窄

    content_rect = fitz.Rect(
        margin_left,
        margin_top,
        page_width - margin_right,
        page_height - margin_bottom,
    )

    # Write initial PDF to a temp file, then add page numbers
    raw_path = output_path.replace(".pdf", "_raw.pdf")
    writer = fitz.DocumentWriter(raw_path)

    more = True
    page_num = 0
    while more:
        page_num += 1
        dev = writer.begin_page(fitz.Rect(0, 0, page_width, page_height))
        more, _ = story.place(content_rect)
        story.draw(dev)
        writer.end_page()

    writer.close()

    # Second pass: add page numbers
    doc = fitz.open(raw_path)
    total = len(doc)
    for i in range(total):
        page = doc[i]
        footer_text = f"— {i + 1} / {total} —"
        text_point = fitz.Point(page_width / 2 - 30, page_height - 36)
        page.insert_text(
            text_point,
            footer_text,
            fontsize=9,
            fontname="helv",
            color=(0.4, 0.4, 0.4),
        )
    doc.save(output_path, deflate=True)
    doc.close()
    try:
        os.remove(raw_path)
    except OSError:
        pass
    print(f"\n  PDF 生成完成: {output_path}")
    print(f"  共 {total} 页")


def main():
    print("=" * 60)
    print("  专利文档 PDF 生成器")
    print("=" * 60)

    # Check files
    print("\n[1/3] 检查源文件...")
    missing = []
    for sec in SECTIONS:
        fp = os.path.join(PATENT_DIR, sec["file"])
        exists = os.path.exists(fp)
        status = "OK" if exists else "MISSING"
        print(f"  {status}: {sec['file']}")
        if not exists:
            missing.append(sec["file"])

    for _, svg_name in SVG_FILES:
        fp = os.path.join(PATENT_DIR, svg_name)
        exists = os.path.exists(fp)
        status = "OK" if exists else "MISSING"
        print(f"  {status}: {svg_name}")

    if missing:
        print(f"\n  [WARN] {len(missing)} 个文件缺失，将跳过对应章节")

    # Build HTML
    print("\n[2/3] 构建 HTML...")
    html = build_full_html()
    print(f"  HTML 内容长度: {len(html)} 字符")

    # Render PDF
    print("\n[3/3] 渲染 PDF...")
    render_pdf(html, CSS, OUTPUT_FILE)

    print("\n" + "=" * 60)
    print("  完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
