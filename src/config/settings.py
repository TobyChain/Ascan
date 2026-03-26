"""
配置管理 - 使用 Pydantic Settings 集中管理
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # 忽略未定义的环境变量
    )
    
    # ==================== LLM 配置 ====================
    api_key: str = Field(..., description="LLM API Key")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API Base URL"
    )
    model_name: str = Field(
        default="gpt-4",
        description="使用的模型名称"
    )
    llm_timeout: int = Field(
        default=120,
        description="LLM 请求超时时间（秒）"
    )
    llm_max_retries: int = Field(
        default=3,
        description="LLM 请求最大重试次数"
    )
    
    # ==================== Jina Reader 配置 ====================
    jina_api_key: str = Field(..., description="Jina Reader API Key")
    jina_timeout: int = Field(
        default=60,
        description="Jina 请求超时时间（秒）"
    )
    jina_max_retries: int = Field(
        default=3,
        description="Jina 请求最大重试次数"
    )
    
    # ==================== 飞书配置 ====================
    feishu_webhook_url: Optional[str] = Field(
        default=None,
        description="飞书机器人 Webhook URL"
    )
    feishu_secret: Optional[str] = Field(
        default=None,
        description="飞书机器人签名密钥"
    )
    feishu_app_id: Optional[str] = Field(
        default=None,
        description="飞书自建应用 App ID"
    )
    feishu_app_secret: Optional[str] = Field(
        default=None,
        description="飞书自建应用 App Secret"
    )
    feishu_docx_folder_token: Optional[str] = Field(
        default=None,
        description="飞书云文档文件夹 Token"
    )
    feishu_docx_base_url: str = Field(
        default="https://ai.feishu.cn/docx",
        description="飞书文档基础 URL"
    )
    
    # ==================== ArXiv 配置 ====================
    arxiv_subjects: List[str] = Field(
        default=["cs.AI"],
        description="要抓取的 ArXiv 主题列表"
    )
    arxiv_date_offset_days: int = Field(
        default=1,
        description="抓取日期偏移（天）"
    )
    max_papers_per_subject: int = Field(
        default=200,
        description="每个主题最大论文数"
    )
    max_total_papers: int = Field(
        default=500,
        description="总共最大论文数"
    )
    
    # ==================== 推荐配置 ====================
    # 高优先级关键词（极度推荐触发词）
    high_priority_keywords: List[str] = Field(
        default=[
            "medical llm", "medical llms",
            "healthcare", "clinical",
            "agent memory", "long-term memory",
            "rag", "retrieval augmented"
        ],
        description="高优先级关键词"
    )
    
    # 头部机构（极度推荐触发）
    top_institutions: List[str] = Field(
        default=[
            "google", "openai", "meta", "deepmind",
            "anthropic", "microsoft", "nvidia",
            "百度", "腾讯", "阿里", "字节", "智谱"
        ],
        description="头部研究机构"
    )
    
    # ==================== 应用配置 ====================
    output_dir: str = Field(
        default="./output",
        description="输出目录"
    )
    database_url: str = Field(
        default="sqlite:////Users/guanbingtao/arXiv-ai-Agent/database/arxiv_papers.db",
        description="数据库连接字符串"
    )
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    enable_feishu_push: bool = Field(
        default=True,
        description="是否启用飞书推送"
    )
    
    @field_validator('arxiv_subjects', mode='before')
    @classmethod
    def parse_subjects(cls, v):
        """解析主题配置（支持逗号分隔字符串或列表）"""
        if isinstance(v, str):
            return [s.strip() for s in v.split(',') if s.strip()]
        return v
    
    @field_validator('high_priority_keywords', 'top_institutions', mode='before')
    @classmethod
    def parse_list(cls, v):
        """解析列表配置"""
        if isinstance(v, str):
            return [s.strip().lower() for s in v.split(',') if s.strip()]
        if isinstance(v, list):
            return [s.lower() for s in v]
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """验证日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}，可选: {valid_levels}")
        return v


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """重新加载配置"""
    global _settings
    _settings = Settings()
    return _settings
