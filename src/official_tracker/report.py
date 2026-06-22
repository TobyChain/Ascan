"""HTML and Markdown report renderers for official tracker."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _safe_join(items: List[str]) -> str:
    return ", ".join([str(item) for item in items if item])


def officials_to_daily_html(
    items: list,
    analyses: Dict[str, Optional[OfficialAnalysis]],
    report_date: str,
) -> str:
    """Generate HTML fragment for the unified daily report."""
    from src.official_tracker.models import OfficialAnalysis  # avoid circular

    articles = [(item, analyses.get(item.slug)) for item in items]
    # Filter out commits without analysis, sort articles by relevance
    relevance_order = {"高度相关": 0, "相关": 1, "一般": 2, "较低": 3}
    articles.sort(key=lambda x: relevance_order.get(x[1].relevance if x[1] else "较低", 9))

    # Count by source
    source_counts: dict[str, int] = {}
    for item, _ in articles:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1

    lines: list[str] = []
    lines.append(f'<p class="meta-note">共发现 {len(items)} 条官方动态，'
                 f'来自 {"、".join(source_counts.keys())}。</p>')

    # Summary table for analyzed articles
    analyzed = [(item, a) for item, a in articles if a is not None]
    if analyzed:
        lines.append('<div class="summary-table-wrapper"><table class="summary-table">')
        lines.append('<thead><tr><th>来源</th><th>标题</th><th>日期</th><th>一句话</th></tr></thead>')
        lines.append('<tbody>')
        for item, a in analyzed[:15]:
            source_label = {"anthropic": "Anthropic", "openai": "OpenAI"}.get(item.source, item.source)
            date_str = item.date or ""
            lines.append(f'<tr><td>{source_label}</td>'
                         f'<td><a href="{item.url}" target="_blank">{item.title[:60]}</a></td>'
                         f'<td>{date_str}</td><td>{a.one_liner}</td></tr>')
        lines.append('</tbody></table></div>')

    # Detailed cards
    lines.append('<div class="detail-cards">')
    for item, a in articles:
        if a is None:
            continue

        source_label = {"anthropic": "Anthropic", "openai": "OpenAI"}.get(item.source, item.source)
        category_tag = f'<span class="tag tag-{item.source}">{item.category or source_label}</span>' if item.category else ""

        lines.append('<div class="card">')
        lines.append(f'<h3><a href="{item.url}" target="_blank">{item.title or item.slug}</a></h3>')
        lines.append(f'<p class="meta-list">{category_tag}'
                     f'<span>📅 {item.date or ""}</span>'
                     f'<span class="relevance-badge relevance-{a.relevance}">{a.relevance}</span></p>')

        if a.one_liner:
            lines.append(f'<p class="lead"><strong>一句话：</strong>{a.one_liner}</p>')
        if a.summary_cn:
            lines.append(f'<div class="abstract-cn"><p>{a.summary_cn}</p></div>')
        if a.core_insight:
            lines.append(f'<p><strong>核心洞察：</strong>{a.core_insight}</p>')
        if a.ecommerce_connection:
            lines.append(f'<p class="ecommerce-rec"><strong>电商关联：</strong>{a.ecommerce_connection}</p>')

        lines.append('</div>')
    lines.append('</div>')

    return "\n".join(lines)


def officials_to_daily_md(
    items: list,
    analyses: Dict[str, Optional[OfficialAnalysis]],
    report_date: str,
) -> str:
    """Generate Markdown fragment for the unified daily report."""
    from src.official_tracker.models import OfficialAnalysis

    lines: list[str] = []
    lines.append(f"共发现 {len(items)} 条官方动态。")
    lines.append("")

    relevance_order = {"高度相关": 0, "相关": 1, "一般": 2, "较低": 3}
    analyzed = [(item, analyses.get(item.slug)) for item in items if analyses.get(item.slug) is not None]
    analyzed.sort(key=lambda x: relevance_order.get(x[1].relevance, 9))

    # Summary table
    if analyzed:
        lines.append("#### 文章速览")
        lines.append("")
        lines.append("| 来源 | 标题 | 日期 | 一句话 |")
        lines.append("|------|------|------|--------|")
        for item, a in analyzed[:15]:
            source_label = {"anthropic": "Anthropic", "openai": "OpenAI"}.get(item.source, item.source)
            date_str = item.date or ""
            lines.append(f"| {source_label} | [{item.title[:40]}]({item.url}) | {date_str} | {a.one_liner} |")
        lines.append("")

    # Detailed analysis
    if analyzed:
        lines.append("#### 深度解析")
        lines.append("")
        for item, a in analyzed:
            source_label = {"anthropic": "Anthropic", "openai": "OpenAI"}.get(item.source, item.source)
            lines.append(f"##### [{item.title or item.slug}]({item.url})")
            lines.append("")
            lines.append(f"**来源：** {source_label} | **日期：** {item.date or ''} | **相关性：** {a.relevance}")
            if item.category:
                lines.append(f"**分类：** {item.category}")
            lines.append("")
            lines.append(f"**一句话：** {a.one_liner}")
            lines.append("")
            lines.append(f"> {a.summary_cn}")
            lines.append("")
            lines.append(f"**核心洞察：** {a.core_insight}")
            lines.append("")
            lines.append(f"**电商关联：** {a.ecommerce_connection}")
            lines.append("")
            lines.append("---")
            lines.append("")

    if not analyzed:
        lines.append("_今日无官方动态更新。_")

    return "\n".join(lines)
