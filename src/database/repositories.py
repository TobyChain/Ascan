"""
数据访问层 - Paper 相关操作
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from loguru import logger

from src.database.models import PaperDB
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
