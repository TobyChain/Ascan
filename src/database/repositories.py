"""
数据访问层 - Paper 相关操作
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from loguru import logger

from src.database.models import PaperDB, RepoDB, OfficialItemDB, BlogPostDB
from src.models.schemas import ArxivPaper, PaperAnalysis


class PaperRepository:
    """论文数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_arxiv_id(self, arxiv_id: str) -> Optional[PaperDB]:
        """根据 ArXiv ID 获取论文"""
        return self.db.query(PaperDB).filter(PaperDB.arxiv_id == arxiv_id).first()
    
    def get_by_id(self, paper_id: int) -> Optional[PaperDB]:
        """根据 ID 获取论文"""
        return self.db.query(PaperDB).filter(PaperDB.id == paper_id).first()
    
    def get_by_date(self, date: str, limit: int = 500) -> List[PaperDB]:
        """获取某一天的论文"""
        return (
            self.db.query(PaperDB)
            .filter(PaperDB.published == date)
            .order_by(desc(PaperDB.recommendation))  # 推荐度高的在前
            .limit(limit)
            .all()
        )
    
    def create_or_update(self, paper: ArxivPaper) -> PaperDB:
        """创建或更新论文"""
        existing = self.get_by_arxiv_id(paper.arxiv_id)
        
        if existing:
            # 更新
            existing.title = paper.title
            existing.authors = paper.authors
            existing.abstract = paper.abstract
            existing.abs_url = paper.abs_url
            existing.pdf_url = paper.pdf_url
            existing.doi = paper.doi
            existing.doi_url = paper.doi_url
            existing.published = paper.published
            existing.bibtex = paper.bibtex
            existing.updated_at = datetime.now()
            
            if paper.analysis:
                existing.trans_abs = paper.analysis.trans_abs
                existing.compressed = paper.analysis.compressed
                existing.keywords = paper.analysis.keywords
                existing.sub_topic = paper.analysis.sub_topic
                existing.recommendation = paper.analysis.recommendation
                existing.one_liner = paper.analysis.one_liner
                existing.core_recommendation = paper.analysis.core_recommendation
            
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # 创建
            db_paper = PaperDB(
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                abs_url=paper.abs_url,
                pdf_url=paper.pdf_url,
                doi=paper.doi,
                doi_url=paper.doi_url,
                published=paper.published,
                bibtex=paper.bibtex,
                trans_abs=paper.analysis.trans_abs if paper.analysis else "",
                compressed=paper.analysis.compressed if paper.analysis else "",
                keywords=paper.analysis.keywords if paper.analysis else [],
                sub_topic=paper.analysis.sub_topic if paper.analysis else "未知",
                recommendation=paper.analysis.recommendation if paper.analysis else "一般推荐",
                one_liner=paper.analysis.one_liner if paper.analysis else None,
                core_recommendation=paper.analysis.core_recommendation if paper.analysis else None,
                status="completed" if paper.analysis else "pending",
                processed_at=datetime.now() if paper.analysis else None
            )
            self.db.add(db_paper)
            self.db.commit()
            self.db.refresh(db_paper)
            return db_paper
    
    def batch_create(self, papers: List[ArxivPaper]) -> List[PaperDB]:
        """批量创建论文"""
        db_papers = []
        for paper in papers:
            db_paper = PaperDB(
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                abs_url=paper.abs_url,
                pdf_url=paper.pdf_url,
                doi=paper.doi,
                doi_url=paper.doi_url,
                published=paper.published,
                bibtex=paper.bibtex,
                status="pending"
            )
            db_papers.append(db_paper)
        
        self.db.bulk_save_objects(db_papers)
        self.db.commit()
        return db_papers
    
    def update_analysis(
        self, 
        arxiv_id: str, 
        analysis: PaperAnalysis,
        status: str = "completed"
    ) -> Optional[PaperDB]:
        """更新论文分析结果"""
        paper = self.get_by_arxiv_id(arxiv_id)
        if not paper:
            return None
        
        paper.trans_abs = analysis.trans_abs
        paper.compressed = analysis.compressed
        paper.keywords = analysis.keywords
        paper.sub_topic = analysis.sub_topic
        paper.recommendation = analysis.recommendation
        paper.status = status
        paper.processed_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(paper)
        return paper
    
    def get_statistics(self, date: Optional[str] = None) -> dict:
        """获取统计信息"""
        query = self.db.query(PaperDB)
        if date:
            query = query.filter(PaperDB.published == date)
        
        total = query.count()
        
        # 按推荐程度统计
        rec_stats = (
            query.with_entities(
                PaperDB.recommendation,
                func.count(PaperDB.id)
            )
            .group_by(PaperDB.recommendation)
            .all()
        )
        
        # 按子主题统计
        subtopic_stats = (
            query.with_entities(
                PaperDB.sub_topic,
                func.count(PaperDB.id)
            )
            .group_by(PaperDB.sub_topic)
            .order_by(desc(func.count(PaperDB.id)))
            .limit(10)
            .all()
        )
        
        return {
            "total": total,
            "by_recommendation": {r: c for r, c in rec_stats},
            "by_subtopic": {s: c for s, c in subtopic_stats}
        }
    
    def get_papers_by_recommendation(
        self, 
        recommendation: str, 
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[PaperDB]:
        """按推荐程度获取论文"""
        query = self.db.query(PaperDB).filter(
            PaperDB.recommendation == recommendation
        )
        if date:
            query = query.filter(PaperDB.published == date)
        
        return query.order_by(desc(PaperDB.created_at)).limit(limit).all()


class RepoRepository:
    """GitHub 仓库数据仓库"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_full_name(self, full_name: str) -> Optional[RepoDB]:
        return self.session.query(RepoDB).filter_by(full_name=full_name).first()

    def upsert(self, repo, today: str) -> RepoDB:
        """Insert or update a repo record. Updates star history and seen tracking."""
        existing = self.get_by_full_name(repo.full_name)
        if existing:
            existing.stars = repo.stars
            existing.forks = repo.forks
            existing.description = repo.description
            existing.pushed_at = repo.pushed_at
            existing.last_seen_date = today
            existing.seen_count = (existing.seen_count or 0) + 1
            history = dict(existing.stars_history or {})
            history[today] = repo.stars
            existing.stars_history = history
            existing.updated_at_ts = datetime.now()
        else:
            existing = RepoDB(
                full_name=repo.full_name,
                owner=repo.owner,
                name=repo.name,
                description=repo.description,
                stars=repo.stars,
                forks=repo.forks,
                language=repo.language,
                topics=repo.topics,
                url=repo.url,
                pushed_at=repo.pushed_at,
                repo_created_at=repo.created_at,
                first_seen_date=today,
                last_seen_date=today,
                seen_count=1,
                stars_history={today: repo.stars},
                analyzed=False,
            )
            self.session.add(existing)
        self.session.commit()
        self.session.refresh(existing)
        return existing

    def save_analysis(self, full_name: str, analysis) -> None:
        """Persist LLM analysis fields to an existing RepoDB row."""
        repo = self.get_by_full_name(full_name)
        if not repo:
            return
        repo.one_liner = analysis.one_liner
        repo.positioning = analysis.positioning
        repo.core_tech = analysis.core_tech
        repo.use_cases = analysis.use_cases
        repo.comparison = analysis.comparison
        repo.watch_reason = analysis.watch_reason
        repo.relevance = analysis.relevance
        repo.analyzed = True
        repo.updated_at_ts = datetime.now()
        self.session.commit()

    def get_recent(self, days: int = 7) -> List[RepoDB]:
        """Return repos seen in the last N days, ordered by stars desc."""
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        return (
            self.session.query(RepoDB)
            .filter(RepoDB.last_seen_date >= cutoff)
            .order_by(desc(RepoDB.stars))
            .all()
        )

    def get_by_date(self, date_str: str) -> List[RepoDB]:
        """Return repos first seen on a specific date."""
        return (
            self.session.query(RepoDB)
            .filter(RepoDB.first_seen_date == date_str)
            .order_by(desc(RepoDB.stars))
            .all()
        )

    def get_all_analyzed_names(self) -> set:
        """Return a set of full_name strings for all repos that have been LLM-analyzed."""
        rows = (
            self.session.query(RepoDB.full_name)
            .filter(RepoDB.analyzed == True, RepoDB.one_liner != None)  # noqa: E712
            .all()
        )
        return {row[0] for row in rows}


class OfficialItemRepository:
    """官方动态跟踪数据仓库"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_slug(self, slug: str) -> Optional[OfficialItemDB]:
        return self.session.query(OfficialItemDB).filter_by(slug=slug).first()

    def get_all_known_slugs(self) -> dict[str, Optional[str]]:
        """返回 {slug: sitemap_lastmod} 用于增量对比"""
        rows = self.session.query(OfficialItemDB.slug, OfficialItemDB.sitemap_lastmod).all()
        return {row[0]: row[1] for row in rows}

    def upsert_discovered(self, slug: str, url: str, title: str, date: str,
                          category: str, item_type: str, summary: str,
                          sitemap_lastmod: Optional[str], today: str) -> OfficialItemDB:
        """发现新条目时插入或更新 last_seen_date"""
        existing = self.get_by_slug(slug)
        if existing:
            existing.last_seen_date = today
            if sitemap_lastmod and sitemap_lastmod != existing.sitemap_lastmod:
                existing.sitemap_lastmod = sitemap_lastmod
                existing.analyzed = False  # 内容更新后重新分析
        else:
            existing = OfficialItemDB(
                source=slug.split(":")[0],  # 格式 "source:actual_slug"
                slug=slug, url=url, title=title, date=date,
                category=category, item_type=item_type, summary=summary,
                sitemap_lastmod=sitemap_lastmod,
                first_seen_date=today, last_seen_date=today, analyzed=False,
            )
            self.session.add(existing)
        self.session.commit()
        self.session.refresh(existing)
        return existing

    def upsert_batch(self, items: list[dict], today: str) -> list[OfficialItemDB]:
        """批量 upsert，items 为 dict 列表"""
        results = []
        for item in items:
            result = self.upsert_discovered(
                slug=item["slug"], url=item["url"], title=item.get("title", ""),
                date=item.get("date", ""), category=item.get("category", ""),
                item_type=item.get("item_type", "article"),
                summary=item.get("summary", ""),
                sitemap_lastmod=item.get("sitemap_lastmod"), today=today,
            )
            results.append(result)
        return results

    def save_scraped_content(self, slug: str, title: str, date: str,
                             category: str, summary: str, content: str) -> None:
        """保存抓取的文章内容"""
        item = self.get_by_slug(slug)
        if not item:
            return
        item.title = title or item.title
        item.date = date or item.date
        item.category = category or item.category
        item.summary = summary or item.summary
        item.content = content
        self.session.commit()

    def save_analysis(self, slug: str, analysis) -> None:
        """保存 LLM 分析结果"""
        item = self.get_by_slug(slug)
        if not item:
            return
        item.one_liner = analysis.one_liner
        item.summary_cn = analysis.summary_cn
        item.core_insight = analysis.core_insight
        item.ecommerce_connection = analysis.ecommerce_connection
        item.relevance = analysis.relevance
        item.analyzed = True
        self.session.commit()

    def get_all_analyzed_slugs(self) -> set[str]:
        """返回已分析过的 slug 集合"""
        rows = (
            self.session.query(OfficialItemDB.slug)
            .filter(OfficialItemDB.analyzed == True, OfficialItemDB.one_liner != None)  # noqa: E712
            .all()
        )
        return {row[0] for row in rows}

    def get_cached_analysis(self, slug: str):
        """从 DB 获取已缓存的分析结果，返回 (source, item)"""
        return self.get_by_slug(slug)


class BlogPostRepository:
    """独立博客订阅数据仓库"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_slug(self, slug: str) -> Optional[BlogPostDB]:
        return self.session.query(BlogPostDB).filter_by(slug=slug).first()

    def get_all_known_slugs(self) -> set[str]:
        """返回已知 slug 集合"""
        rows = self.session.query(BlogPostDB.slug).all()
        return {row[0] for row in rows}

    def upsert_discovered(self, slug: str, url: str, title: str, date: str,
                          source_label: str, summary: str, today: str) -> BlogPostDB:
        """发现新博文时插入"""
        existing = self.get_by_slug(slug)
        if existing:
            existing.last_seen_date = today
        else:
            existing = BlogPostDB(
                source=slug.split(":")[0],
                slug=slug, url=url, title=title, date=date,
                source_label=source_label, summary=summary,
                first_seen_date=today, last_seen_date=today, analyzed=False,
            )
            self.session.add(existing)
        self.session.commit()
        self.session.refresh(existing)
        return existing

    def save_scraped_content(self, slug: str, content: str) -> None:
        """保存博客正文内容"""
        post = self.get_by_slug(slug)
        if post:
            post.content = content
            self.session.commit()

    def save_analysis(self, slug: str, analysis) -> None:
        """保存 LLM 分析结果"""
        post = self.get_by_slug(slug)
        if not post:
            return
        post.one_liner = analysis.one_liner
        post.summary_cn = analysis.summary_cn
        post.ecommerce_connection = analysis.ecommerce_connection
        post.relevance = analysis.relevance
        post.analyzed = True
        self.session.commit()

    def get_all_analyzed_slugs(self) -> set[str]:
        """返回已分析过的 slug 集合"""
        rows = (
            self.session.query(BlogPostDB.slug)
            .filter(BlogPostDB.analyzed == True, BlogPostDB.one_liner != None)  # noqa: E712
            .all()
        )
        return {row[0] for row in rows}
