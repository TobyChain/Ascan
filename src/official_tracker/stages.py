"""Official Tracker Pipeline Stages.

FetchOfficialStage    -> fetch from Anthropic/OpenAI, merge, detect new
EnrichArticlesStage   -> scrape article content for new articles
AnalyzeOfficialStage  -> LLM batch analysis
BuildOfficialFragmentStage -> generate HTML + MD fragments
"""
from __future__ import annotations

from typing import Optional

from loguru import logger

from src.pipeline.core import PipelineStage, PipelineContext, Stage, Status
from src.official_tracker.fetcher import OfficialFetcher
from src.official_tracker.models import OfficialItem, OfficialAnalysis
from src.official_tracker.analyzer import analyze_articles_batch
from src.official_tracker.report import officials_to_daily_html, officials_to_daily_md
from src.database.connection import get_db_session
from src.database.repositories import OfficialItemRepository
from src.config.settings import get_settings


# ── Stage 1: Fetch ──────────────────────────────────────────────────────────

class FetchOfficialStage(PipelineStage):
    """Fetch from all official sources, detect new vs already-known."""

    def __init__(self):
        super().__init__("fetching_official")

    async def execute(self, context: PipelineContext) -> bool:
        settings = get_settings()
        fetcher = OfficialFetcher(github_token=settings.github_token)
        db = get_db_session()
        repo = OfficialItemRepository(db)

        known_slugs = repo.get_all_known_slugs()
        today = context.date.replace("-", "")

        all_items_data = []

        # ── Source 1: Anthropic Research ──────────────────────────────
        try:
            anth_items = fetcher.fetch_anthropic_sitemap(settings.anthropic_sitemap_url)
            all_items_data.extend(anth_items)
            logger.info(f"Anthropic: {len(anth_items)} articles from sitemap")
        except Exception as e:
            logger.warning(f"Anthropic fetch failed: {e}")

        # ── Source 2: OpenAI Research ─────────────────────────────────
        try:
            openai_items = fetcher.fetch_openai_sitemap(settings.openai_research_sitemap_url)
            all_items_data.extend(openai_items)
            logger.info(f"OpenAI: {len(openai_items)} articles from sitemap")
        except Exception as e:
            logger.warning(f"OpenAI fetch failed: {e}")

        # ── Incremental detection ─────────────────────────────────────
        new_items = []
        updated_items = []

        for item_data in all_items_data:
            slug = item_data["slug"]
            lastmod = item_data.get("lastmod")

            if slug not in known_slugs:
                new_items.append(item_data)
            elif lastmod and known_slugs.get(slug) != lastmod:
                updated_items.append(item_data)

        # Upsert all to DB
        all_to_upsert = new_items + updated_items
        if all_to_upsert:
            repo.upsert_batch(all_to_upsert, today)
            logger.success(f"Upserted {len(all_to_upsert)} items ({len(new_items)} new, {len(updated_items)} updated)")

        # Convert to OfficialItem objects
        official_items = []
        for item_data in all_to_upsert:
            source = item_data["slug"].split(":")[0]
            official_items.append(OfficialItem(
                source=source,
                slug=item_data["slug"],
                url=item_data["url"],
                title=item_data.get("title"),
                date=item_data.get("date") or item_data.get("lastmod", "")[:10] if item_data.get("lastmod") else None,
                category=item_data.get("category"),
                item_type=item_data.get("item_type", "article"),
                summary=item_data.get("summary"),
                sitemap_lastmod=item_data.get("lastmod"),
            ))

        # Get set of already-analyzed slugs
        analyzed_slugs = repo.get_all_analyzed_slugs()

        context.official_items = official_items
        context.official_analyzed_slugs = analyzed_slugs
        logger.success(f"Fetch done: {len(official_items)} new/updated items, {len(analyzed_slugs)} already analyzed")
        return True


# ── Stage 2: Enrich ────────────────────────────────────────────────────────

class EnrichArticlesStage(PipelineStage):
    """Scrape article content for new articles (skip commits and already-enriched)."""

    def __init__(self):
        super().__init__("enriching_official")

    async def execute(self, context: PipelineContext) -> bool:
        items: list[OfficialItem] = context.official_items
        if not items:
            logger.info("No items to enrich, skipping")
            return True

        settings = get_settings()
        fetcher = OfficialFetcher(github_token=settings.github_token)
        db = get_db_session()
        repo = OfficialItemRepository(db)

        # Only scrape articles without content and not commits
        to_scrape = [item for item in items if item.item_type == "article" and not item.content]
        if not to_scrape:
            logger.info("No articles to scrape, skipping")
            return True

        logger.info(f"Scraping content for {len(to_scrape)} articles...")
        enriched = fetcher.scrape_articles_batch(to_scrape, delay=settings.official_scrape_delay)

        # Save scraped content to DB
        for item in enriched:
            if item.content:
                repo.save_scraped_content(item.slug, item.title or "", item.date or "",
                                          item.category or "", item.summary or "", item.content or "")

        # Replace in context
        slug_map = {item.slug: item for item in enriched}
        context.official_items = [slug_map.get(item.slug, item) for item in items]

        logger.success(f"Enrich done: {len(to_scrape)} articles scraped")
        return True


# ── Stage 3: Analyze ───────────────────────────────────────────────────────

class AnalyzeOfficialStage(PipelineStage):
    """LLM batch analysis of new articles, skip already-analyzed ones."""

    def __init__(self):
        super().__init__("analyzing_official")

    async def execute(self, context: PipelineContext) -> bool:
        items: list[OfficialItem] = context.official_items
        if not items:
            logger.info("No items to analyze, skipping")
            context.official_analyses = {}
            return True

        db = get_db_session()
        repo = OfficialItemRepository(db)
        analyzed_slugs: set[str] = getattr(context, "official_analyzed_slugs", set())

        analyses: dict[str, Optional[OfficialAnalysis]] = {}

        # ── Pass 1: restore already-analyzed from DB ──────────────────
        cached_count = 0
        for item in items:
            if item.slug not in analyzed_slugs:
                continue
            row = repo.get_cached_analysis(item.slug)
            if row and row.analyzed and row.one_liner:
                analyses[item.slug] = OfficialAnalysis(
                    one_liner=row.one_liner or "",
                    summary_cn=row.summary_cn or "",
                    core_insight=row.core_insight or "",
                    ecommerce_connection=row.ecommerce_connection or "",
                    relevance=row.relevance or "一般",
                )
                cached_count += 1

        # ── Pass 2: LLM 并发分析 ─────────────────────────────────────
        to_analyze = [item for item in items if item.slug not in analyses]
        logger.info(f"Analyze: {len(items)} total, {cached_count} cached, {len(to_analyze)} need LLM")

        if to_analyze:
            from src.tools.call_llm import LLMClient
            client = LLMClient()

            new_analyses = await analyze_articles_batch(to_analyze, client=client)
            analyses.update(new_analyses)

            # Save to DB
            for slug, analysis in new_analyses.items():
                if analysis:
                    try:
                        repo.save_analysis(slug, analysis)
                    except Exception as e:
                        logger.warning(f"Failed to save analysis for {slug}: {e}")

        context.official_analyses = analyses
        success_count = sum(1 for a in analyses.values() if a is not None)
        logger.success(
            f"Analysis done: {success_count}/{len(items)} "
            f"({cached_count} cached, {len(to_analyze)} new LLM calls)"
        )
        return True


# ── Stage 4: Build Fragment ────────────────────────────────────────────────

class BuildOfficialFragmentStage(PipelineStage):
    """Generate HTML + MD fragments for the unified daily report."""

    def __init__(self):
        super().__init__("building_fragment_official")

    async def execute(self, context: PipelineContext) -> bool:
        items: list[OfficialItem] = context.official_items
        analyses: dict[str, Optional[OfficialAnalysis]] = context.official_analyses

        if not items:
            logger.info("No items for official report, using placeholder")
            context.official_html = '<p class="empty-state">今日无 Anthropic Research 或 OpenAI 新文章。</p>'
            context.official_md = "_今日无 Anthropic Research 或 OpenAI 新文章。_"
            return True

        date_compact = context.date.replace("-", "")
        html_fragment = officials_to_daily_html(items, analyses, date_compact)
        md_fragment = officials_to_daily_md(items, analyses, date_compact)

        context.official_html = html_fragment
        context.official_md = md_fragment
        logger.success(f"Official HTML+MD 片段已生成 (HTML: {len(html_fragment)} chars)")
        return True
