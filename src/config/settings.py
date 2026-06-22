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
    
    # ==================== LLM 配置（IdealAb OpenAI 兼容 API）====================
    idealab_api_key: str = Field(
        default="",
        description="IdealAb API Key"
    )
    idealab_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API Base URL（OpenAI 兼容）"
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM 模型名称（OpenAI 兼容；如 gpt-4o-mini / qwen-plus / claude-3-5-sonnet 等）"
    )
    llm_timeout: int = Field(
        default=120,
        description="LLM 请求超时时间（秒）"
    )
    llm_max_retries: int = Field(
        default=3,
        description="LLM 请求最大重试次数"
    )

    # ==================== GitHub Agent 配置 ====================
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token (public_repo read scope)"
    )
    github_topics: List[str] = Field(
        default=[
            "digital-twin", "digital-avatar", "virtual-human",
            "recommendation-system", "product-recommendation", "e-commerce",
            "product-inspection", "compliance-detection", "content-moderation",
            "customer-service", "chatbot", "conversational-ai",
            "llm-agent", "ai-agent", "rag", "multi-agent",
        ],
        description="GitHub topic labels to search"
    )
    github_max_repos_per_topic: int = Field(
        default=8,
        description="每个 topic 最多抓取的仓库数"
    )
    github_min_stars: int = Field(
        default=500,
        description="最低 star 数过滤"
    )
    github_top_analyze: int = Field(
        default=20,
        description="送入 LLM 深度分析的 Top N 仓库数（分析结果用于相关性过滤表格）"
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
            # 数字员工 / 虚拟人
            "digital worker", "digital employee", "digital human",
            "digital human", "avatar generation", "face cloning",
            "talking head", "face reenactment",
            # 商品推荐 / 电商推荐
            "product recommendation", "e-commerce recommendation",
            "item recommendation", "sequential recommendation",
            "collaborative filtering", "click-through rate",
            # 商品巡检 / 合规检测
            "product inspection", "compliance detection",
            "content moderation", "image classification",
            "counterfeit detection", "product quality",
            "violation detection", "risk detection",
            # 电商客服 / 对话系统
            "customer service", "e-commerce chatbot",
            "conversational ai", "dialogue system",
            "customer support", "after-sales service",
            # 通用 AI Agent
            "llm agent", "ai agent", "rag",
            "multi-agent", "agent framework",
        ],
        description="高优先级关键词（极度推荐触发）"
    )

    # 头部机构（极度推荐触发）
    top_institutions: List[str] = Field(
        default=[
            "google", "openai", "meta", "deepmind",
            "anthropic", "microsoft", "apple", "samsung",
            "xiaomi", "huawei", "oppo",
            "百度", "腾讯", "阿里", "字节", "智谱"
        ],
        description="头部研究机构"
    )
    
    # ==================== 应用配置 ====================
    output_dir: str = Field(
        default="./docs",
        description="输出目录"
    )
    database_url: str = Field(
        default="sqlite:///./database/arxiv_papers.db",
        description="数据库连接字符串"
    )
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )

    # ==================== 飞书推送 / Jina ====================
    enable_feishu_push: bool = Field(
        default=False,
        description="是否启用飞书推送（UploadStage / NotifyStage）"
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
        description="飞书文档上传目标文件夹 Token"
    )
    feishu_docx_base_url: str = Field(
        default="https://feishu.cn/docx",
        description="飞书文档基础 URL"
    )
    feishu_webhook_url: Optional[str] = Field(
        default=None,
        description="飞书机器人 Webhook URL（用于卡片通知）"
    )

    jina_api_key: Optional[str] = Field(
        default=None,
        description="Jina Reader API Key（可选；为空时走免费匿名访问）"
    )
    jina_base_url: str = Field(
        default="https://r.jina.ai",
        description="Jina Reader 基础 URL"
    )

    # ==================== 官方动态跟踪配置 ====================
    anthropic_sitemap_url: str = Field(
        default="https://www.anthropic.com/sitemap.xml",
        description="Anthropic Research sitemap URL"
    )
    openai_research_sitemap_url: str = Field(
        default="https://openai.com/sitemap.xml/research/",
        description="OpenAI Research sitemap URL"
    )
    official_scrape_delay: float = Field(
        default=1.0,
        description="文章抓取间隔秒数（礼貌爬取）"
    )

    # ==================== 独立博客 RSS 源配置 ====================
    blog_rss_sources: List[dict] = Field(
        default=[
            {"name": "ruanyifeng", "url": "https://www.ruanyifeng.com/blog/atom.xml", "label": "阮一峰周刊"},
            {"name": "sebastian", "url": "https://magazine.sebastianraschka.com/feed", "label": "Sebastian Raschka"},
            {"name": "lilianweng", "url": "https://lilianweng.github.io/index.xml", "label": "Lilian Weng"},
        ],
        description="独立博客 RSS 源列表"
    )

    @field_validator('github_topics', mode='before')
    @classmethod
    def parse_github_topics(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(',') if t.strip()]
        return v

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
