"""HTML and Markdown report renderers for blog subscriptions — 纯 RSS 摘要+链接，无 LLM 分析。"""
from __future__ import annotations

from typing import List


def blogs_to_daily_html(posts: list, report_date: str) -> str:
    """Generate HTML fragment — just title, date, link, RSS summary."""
    lines: list[str] = []
    lines.append(f'<p class="meta-note">共 {len(posts)} 篇新文章。</p>')

    # Group by source
    source_posts: dict[str, list] = {}
    for post in posts:
        source_posts.setdefault(post.source_label, []).append(post)

    for source_label, src_posts in source_posts.items():
        lines.append(f'<h3 class="source-heading">📝 {source_label}</h3>')
        lines.append('<div class="summary-table-wrapper"><table class="summary-table">')
        lines.append('<thead><tr><th>日期</th><th>标题</th><th>摘要</th></tr></thead>')
        lines.append('<tbody>')
        for post in src_posts:
            date_str = post.date or ""
            title_display = (post.title or post.slug)[:60]
            summary_display = (post.summary or "")[:100]
            lines.append(f'<tr><td>{date_str}</td>'
                         f'<td><a href="{post.url}" target="_blank">{title_display}</a></td>'
                         f'<td>{summary_display}</td></tr>')
        lines.append('</tbody></table></div>')

    return "\n".join(lines)


def blogs_to_daily_md(posts: list, report_date: str) -> str:
    """Generate Markdown fragment — just title, date, link, RSS summary."""
    lines: list[str] = []
    lines.append(f"共 {len(posts)} 篇新文章。")
    lines.append("")

    source_posts: dict[str, list] = {}
    for post in posts:
        source_posts.setdefault(post.source_label, []).append(post)

    for source_label, src_posts in source_posts.items():
        lines.append(f"### 📝 {source_label}")
        lines.append("")
        for post in src_posts:
            date_str = post.date or ""
            summary_display = (post.summary or "")[:100]
            lines.append(f"- [{post.title or post.slug}]({post.url}) ({date_str})")
            if summary_display:
                lines.append(f"  > {summary_display}")
        lines.append("")

    return "\n".join(lines)
