"""Blog Subscription Pipeline Stages — 无 LLM 分析，有更新就生成摘要+链接。

FetchBlogStage      -> fetch RSS feeds, detect new posts
BuildBlogFragmentStage -> generate HTML + MD (no LLM)
"""
from __future__ import annotations

from loguru import logger

from src.pipeline.core import PipelineStage, PipelineContext, Stage, Status
from src.blog_subs.rss_parser import fetch_all_feeds
from src.blog_subs.models import BlogPost
from src.blog_subs.report import blogs_to_daily_html, blogs_to_daily_md
from src.database.connection import get_db_session
from src.database.repositories import BlogPostRepository


# ── Stage 1: Fetch ──────────────────────────────────────────────────────────

class FetchBlogStage(PipelineStage):
    """Fetch all RSS feeds, detect new posts."""

    def __init__(self):
        super().__init__("fetching_blog")

    async def execute(self, context: PipelineContext) -> bool:
        db = get_db_session()
        repo = BlogPostRepository(db)

        known_slugs = repo.get_all_known_slugs()
        today = context.date.replace("-", "")

        all_posts = fetch_all_feeds()
        new_posts = [post for post in all_posts if post.slug not in known_slugs]

        # Upsert new posts to DB
        for post in new_posts:
            repo.upsert_discovered(
                slug=post.slug, url=post.url, title=post.title or "",
                date=post.date or "", source_label=post.source_label,
                summary=post.summary or "", today=today,
            )

        if new_posts:
            logger.success(f"发现 {len(new_posts)} 篇新博客文章（共 {len(all_posts)} 篇已知）")
        else:
            logger.info(f"无新博客文章（{len(all_posts)} 篇全部已读）")

        context.blog_posts = new_posts
        return True


# ── Stage 2: Build Fragment (no LLM) ────────────────────────────────────────

class BuildBlogFragmentStage(PipelineStage):
    """Generate HTML + MD fragments — direct from RSS data, no LLM."""

    def __init__(self):
        super().__init__("building_fragment_blog")

    async def execute(self, context: PipelineContext) -> bool:
        posts: list[BlogPost] = context.blog_posts

        if not posts:
            logger.info("无博客帖子，使用占位符")
            context.blog_html = '<p class="empty-state">今日无独立博客更新。</p>'
            context.blog_md = "_今日无独立博客更新。_"
            return True

        date_compact = context.date.replace("-", "")
        html_fragment = blogs_to_daily_html(posts, date_compact)
        md_fragment = blogs_to_daily_md(posts, date_compact)

        context.blog_html = html_fragment
        context.blog_md = md_fragment
        logger.success(f"博客 HTML+MD 片段已生成 (HTML: {len(html_fragment)} chars, {len(posts)} 篇)")
        return True
