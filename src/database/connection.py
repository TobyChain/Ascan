"""
数据库连接管理
"""

import time
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from loguru import logger

from src.config.settings import get_settings


def get_engine():
    """创建数据库引擎"""
    settings = get_settings()
    
    # SQLite 特殊配置：使用 StaticPool 避免多线程问题
    if settings.database_url.startswith("sqlite"):
        engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.log_level == "DEBUG"
        )
    else:
        engine = create_engine(settings.database_url)
    
    # 添加事件监听，记录慢查询
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - context._query_start_time
        if total_time > 1.0:  # 慢查询阈值 1 秒
            logger.warning(f"慢查询 ({total_time:.2f}s): {statement[:100]}...")
    
    return engine


# 全局引擎实例
_engine = None
_SessionLocal = None


def init_database():
    """初始化数据库"""
    global _engine, _SessionLocal
    
    _engine = get_engine()
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # 创建所有表
    from src.database.models import Base
    Base.metadata.create_all(bind=_engine)
    logger.success("数据库初始化完成")


def get_db() -> Session:
    """获取数据库会话（用于依赖注入）"""
    global _SessionLocal
    
    if _SessionLocal is None:
        init_database()
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """直接获取数据库会话"""
    global _SessionLocal
    
    if _SessionLocal is None:
        init_database()
    
    return _SessionLocal()
