"""
数据库模型定义 - SQLAlchemy ORM
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    Float, ForeignKey, JSON, create_engine, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class PaperDB(Base):
    """论文数据表"""
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    arxiv_id = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    authors = Column(JSON, default=list)  # 存储为 JSON 数组
    abstract = Column(Text, default="")
    abs_url = Column(String(500), nullable=False)
    pdf_url = Column(String(500), nullable=True)
    doi = Column(String(100), nullable=True)
    doi_url = Column(String(500), nullable=True)
    published = Column(String(10), index=True)  # YYYY-MM-DD
    bibtex = Column(Text, nullable=True)
    
    # 机构和主图
    affiliations = Column(JSON, default=list)  # 作者机构列表
    primary_image_url = Column(String(500), nullable=True)  # 主图URL
    
    # LLM 分析结果
    trans_abs = Column(Text, default="")
    compressed = Column(Text, default="")
    keywords = Column(JSON, default=list)
    sub_topic = Column(String(100), index=True, default="未知")
    recommendation = Column(String(20), index=True, default="一般推荐")
    
    # 处理状态
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # 关联
    daily_reports = relationship(
        "DailyReportDB", 
        secondary="paper_daily_report",
        back_populates="papers"
    )
    
    def __repr__(self):
        return f"<Paper({self.arxiv_id}: {self.title[:50]}...)>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors or [],
            "affiliations": self.affiliations or [],
            "primary_image_url": self.primary_image_url,
            "abstract": self.abstract,
            "abs_url": self.abs_url,
            "pdf_url": self.pdf_url,
            "doi": self.doi,
            "doi_url": self.doi_url,
            "published": self.published,
            "bibtex": self.bibtex,
            "trans_abs": self.trans_abs,
            "compressed": self.compressed,
            "keywords": self.keywords or [],
            "sub_topic": self.sub_topic,
            "recommendation": self.recommendation,
            "status": self.status,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class DailyReportDB(Base):
    """每日报告表"""
    __tablename__ = "daily_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), unique=True, index=True, nullable=False)  # YYYY-MM-DD
    total_count = Column(Integer, default=0)
    highly_recommended_count = Column(Integer, default=0)
    recommended_count = Column(Integer, default=0)
    file_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")  # pending, generating, completed, failed
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # 关联
    papers = relationship(
        "PaperDB",
        secondary="paper_daily_report",
        back_populates="daily_reports"
    )
    
    def __repr__(self):
        return f"<DailyReport({self.date}: {self.total_count} papers)>"


class PaperDailyReport(Base):
    """论文与日报的关联表"""
    __tablename__ = "paper_daily_report"
    
    paper_id = Column(Integer, ForeignKey("papers.id"), primary_key=True)
    daily_report_id = Column(Integer, ForeignKey("daily_reports.id"), primary_key=True)


class ProcessingLogDB(Base):
    """处理日志表 - 用于追踪状态"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(10), index=True, nullable=False)
    stage = Column(String(50), nullable=False)  # fetching, parsing, analyzing, etc.
    status = Column(String(20), nullable=False)  # started, success, failed
    message = Column(Text, nullable=True)
    progress = Column(Integer, default=0)  # 0-100
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_date_stage', 'date', 'stage'),
    )
    
    def __repr__(self):
        return f"<ProcessingLog({self.date} {self.stage}: {self.status})>"


class UserFeedbackDB(Base):
    """用户反馈表 - 用于优化推荐"""
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 评分
    is_interested = Column(Integer, default=0)  # 0/1
    is_read = Column(Integer, default=0)  # 0/1
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 关联
    paper = relationship("PaperDB")
    
    def __repr__(self):
        return f"<UserFeedback(paper={self.paper_id}, rating={self.rating})>"


class ArxivSubjectStatDB(Base):
    """ArXiv 主题统计表"""
    __tablename__ = "arxiv_subject_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    subject_code = Column(String(20), index=True, nullable=False)  # cs.AI
    date = Column(String(10), index=True, nullable=False)
    paper_count = Column(Integer, default=0)
    fetched_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_subject_date', 'subject_code', 'date', unique=True),
    )
