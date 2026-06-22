"""LLM analysis for official tracker articles."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Optional

from loguru import logger

from src.official_tracker.models import OfficialItem, OfficialAnalysis


def _build_article_prompt(item: OfficialItem) -> str:
    """Construct LLM prompt for analyzing an official article."""
    content_preview = (item.content or item.summary or "")[:1500]

    return f"""你是一位电商AI应用研究专家。请分析以下技术文章，输出JSON格式的分析结果。

## 文章信息
- 标题：{item.title or "未知"}
- 日期：{item.date or "未知"}
- 来源：{item.source}
- 分类：{item.category or "未知"}
- 摘要：{item.summary or ""}
- 内容摘要（前1500字）：{content_preview}

## 分析要求
请输出严格的 JSON 对象，包含以下字段：
- one_liner: 用大白话说清这篇研究/更新讲了什么（中文，≤30字）
- summary_cn: 中文摘要（2-3句）
- core_insight: 核心技术洞察或贡献（中文，2-3句）
- ecommerce_connection: 与电商AI应用的关联（中文，1-2句），如客服、推荐、巡检、智能体等
- relevance: 与电商AI应用的相关性，只能是"高度相关"或"相关"或"一般"或"较低" 中的一个

只输出 JSON，不要其他内容。"""


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    if not text:
        return None
    # Try to find JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def analyze_item(item: OfficialItem, client=None) -> Optional[OfficialAnalysis]:
    """Analyze a single article using LLM. Returns None for commits."""
    if item.item_type == "commit":
        return None

    if client is None:
        from src.tools.call_llm import LLMClient
        client = LLMClient()

    prompt = _build_article_prompt(item)

    for attempt in range(3):
        try:
            resp = client.chat(prompt)
            data = _extract_json(resp)
            if not data:
                logger.warning(f"JSON extraction failed for {item.slug} (attempt {attempt+1})")
                continue

            # Normalize relevance
            valid_relevance = {"高度相关", "相关", "一般", "较低"}
            rel = data.get("relevance", "一般")
            if rel not in valid_relevance:
                rel = "一般"
            data["relevance"] = rel

            return OfficialAnalysis(
                one_liner=data.get("one_liner", ""),
                summary_cn=data.get("summary_cn", ""),
                core_insight=data.get("core_insight", ""),
                ecommerce_connection=data.get("ecommerce_connection", ""),
                relevance=rel,
            )
        except Exception as e:
            logger.warning(f"LLM analysis failed for {item.slug} (attempt {attempt+1}): {e}")

    logger.error(f"LLM analysis failed after 3 retries for {item.slug}")
    return None


async def analyze_item_async(item: OfficialItem, client=None) -> Optional[OfficialAnalysis]:
    """Async wrapper for analyze_item with concurrency control."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: analyze_item(item, client))


async def analyze_articles_batch(
    items: list[OfficialItem],
    max_concurrency: int = 15,
    client=None,
) -> dict[str, Optional[OfficialAnalysis]]:
    """Analyze multiple articles concurrently. Returns {slug: analysis}."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _limited(item):
        async with semaphore:
            return item.slug, await analyze_item_async(item, client)

    tasks = [_limited(item) for item in items if item.item_type != "commit"]
    results = await asyncio.gather(*tasks)

    analysis_map = dict(results)

    # Add commits as None
    for item in items:
        if item.item_type == "commit":
            analysis_map[item.slug] = None

    return analysis_map
