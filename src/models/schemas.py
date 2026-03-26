"""
数据模型定义 - 使用 Pydantic 进行结构化验证
"""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re


class PaperAnalysis(BaseModel):
    """LLM 分析结果的数据模型"""
    
    trans_abs: str = Field(
        ..., 
        min_length=10,
        description="中文翻译摘要"
    )
    compressed: str = Field(
        ..., 
        min_length=5,
        max_length=500,
        description="2-3句话的压缩版本"
    )
    keywords: List[str] = Field(
        ..., 
        min_length=2,
        max_length=5,
        description="3-5个关键词"
    )
    sub_topic: str = Field(
        ..., 
        min_length=2,
        description="子主题/细分领域"
    )
    recommendation: Literal[
        "极度推荐", "很推荐", "推荐", "一般推荐", "不推荐"
    ] = Field(
        default="一般推荐",
        description="推荐程度"
    )
    
    @field_validator('keywords', mode='before')
    @classmethod
    def validate_keywords(cls, v):
        """确保关键词是非空字符串列表"""
        if isinstance(v, str):
            # 如果是逗号分隔的字符串，转换为列表
            v = [k.strip() for k in v.split(',') if k.strip()]
        if not isinstance(v, list):
            raise ValueError("keywords 必须是列表")
        # 过滤空字符串
        v = [k for k in v if k and isinstance(k, str)]
        if len(v) < 2:
            raise ValueError("至少需要2个关键词")
        return v[:5]  # 最多保留5个
    
    @field_validator('recommendation', mode='before')
    @classmethod
    def validate_recommendation(cls, v):
        """标准化推荐程度文本"""
        if not v:
            return "一般推荐"
        v = str(v).strip()
        valid_values = ["极度推荐", "很推荐", "推荐", "一般推荐", "不推荐"]
        # 模糊匹配
        for valid in valid_values:
            if valid in v or v in valid:
                return valid
        return "一般推荐"


class ArxivPaper(BaseModel):
    """ArXiv 论文数据模型"""
    
    arxiv_id: str = Field(..., description="ArXiv ID")
    title: str = Field(..., min_length=1, description="论文标题")
    authors: List[str] = Field(default=[], description="作者列表")
    abstract: str = Field(default="", description="英文摘要")
    summary: str = Field(default="", description="原始摘要（兼容字段）")
    abs_url: str = Field(..., description="ArXiv 摘要页面 URL")
    pdf_url: Optional[str] = Field(default=None, description="PDF 下载链接")
    doi: Optional[str] = Field(default=None, description="DOI")
    doi_url: Optional[str] = Field(default=None, description="DOI 链接")
    published: str = Field(..., description="发布日期")
    bibtex: Optional[str] = Field(default=None, description="BibTeX 引用")
    
    # LLM 分析结果
    analysis: Optional[PaperAnalysis] = Field(default=None, description="分析结果")
    
    # 处理状态
    processed_at: Optional[datetime] = Field(default=None, description="处理时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    
    @field_validator('arxiv_id')
    @classmethod
    def validate_arxiv_id(cls, v):
        """验证 ArXiv ID 格式"""
        v = str(v).strip()
        # 支持格式: 2512.13510 或 2025.12345 或带v版本的 2512.13510v1
        pattern = r'^\d{4}\.\d{4,5}(v\d+)?$'
        if not re.match(pattern, v):
            raise ValueError(f"无效的 ArXiv ID 格式: {v}")
        return v
    
    @field_validator('published', mode='before')
    @classmethod
    def validate_published(cls, v):
        """标准化日期格式"""
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, str):
            # 尝试多种格式
            for fmt in ["%Y-%m-%d", "%a, %d %b %Y", "%d %b %Y"]:
                try:
                    dt = datetime.strptime(v.strip(), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return v
    
    @field_validator('abs_url')
    @classmethod
    def validate_abs_url(cls, v):
        """确保 abs_url 完整"""
        v = str(v).strip()
        if not v.startswith('http'):
            raise ValueError(f"无效的 URL: {v}")
        return v


class DailyReport(BaseModel):
    """每日报告数据模型"""
    
    date: str = Field(..., description="报告日期")
    papers: List[ArxivPaper] = Field(default=[], description="论文列表")
    total_count: int = Field(default=0, description="论文总数")
    highly_recommended: int = Field(default=0, description="高度推荐数量")
    file_url: Optional[str] = Field(default=None, description="飞书文档链接")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    @field_validator('total_count', mode='before')
    @classmethod
    def calculate_total(cls, v, info):
        """自动计算总数"""
        if v == 0 and 'papers' in info.data:
            return len(info.data['papers'])
        return v


class ProcessingState(BaseModel):
    """处理状态追踪模型"""
    
    date: str = Field(..., description="处理日期")
    stage: Literal[
        "fetching", "parsing", "analyzing", "generating", "uploading", "completed", "failed"
    ] = Field(default="fetching", description="当前阶段")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    message: Optional[str] = Field(default=None, description="状态消息")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    error: Optional[str] = Field(default=None, description="错误信息")
