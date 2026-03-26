"""md_report.py

把 arxiv_daily 处理结果渲染为简洁 Markdown。
"""

from __future__ import annotations

from typing import Any, Dict, List


def _safe_join(items: List[str]) -> str:
    return ", ".join([i for i in items if i])


def _escape_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def papers_to_markdown(date_str: str, papers: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    # 按照要求，直接以分割线开始，不再保留顶部的总标题和论文数
    lines.append("---")

    # 英文到中文的映射
    sub_topic_map = {
        "medical_llm": "医学大模型",
        "moe": "混合专家模型",
        "lora": "低秩适配",
        "rag": "检索增强生成",
        "agent": "智能体系统",
        "multimodal": "多模态模型",
        "reasoning": "推理能力",
        "alignment": "对齐技术",
        "unknown": "未知",
        "未知": "未知"
    }

    for idx, p in enumerate(papers, start=1):
        title = (p.get("title") or "").strip()
        authors = p.get("authors") or []
        abs_url = p.get("abs_url") or ""
        pdf_url = p.get("pdf_url") or ""
        
        # 转换子主题为中文
        sub_topic_en = p.get("sub_topic") or "未知"
        sub_topic = sub_topic_map.get(sub_topic_en, sub_topic_en)
        
        recommendation = p.get("recommendation") or "一般推荐"
        keywords = p.get("keywords") or []
        trans_abs = (p.get("trans_abs") or "").strip()

        lines.append(f"## {idx}. {title}")
        lines.append("")
        if authors:
            lines.append(f"- 作者：{_safe_join(authors)}")
        lines.append(f"- 研究方向：{sub_topic}")
        lines.append(f"- 推荐：{recommendation}")
        if keywords:
            lines.append(f"- 关键词：{_safe_join(list(map(str, keywords)))}")
        if abs_url:
            lines.append(f"- Abstract：{abs_url}")
        if pdf_url:
            lines.append(f"- PDF：{pdf_url}")

        lines.append("")
        if trans_abs:
            lines.append("**中文摘要**")
            lines.append("")
            lines.append(trans_abs)
            lines.append("")
        else:
            # 如果没有中文摘要，使用英文摘要或评分信息
            lines.append("**中文摘要**")
            lines.append("")
            lines.append("*中文摘要生成中...*")
            lines.append("")
        lines.append("---")

    return "\n".join(lines).rstrip() + "\n"
