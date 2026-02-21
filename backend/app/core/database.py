"""
数据库连接模块 (Database Connection Module)

基于 SQLAlchemy 2.0 异步模式创建数据库引擎和会话管理，为 VigilOps 平台提供数据持久化支持。
包含异步引擎创建、会话工厂配置、ORM 基类定义和依赖注入函数。

Creates database engine and session management based on SQLAlchemy 2.0 async mode,
providing data persistence support for the VigilOps platform. Includes async engine
creation, session factory configuration, ORM base class definition, and dependency injection functions.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 创建异步数据库引擎 (Create Async Database Engine)
# 使用 asyncpg 驱动连接 PostgreSQL，支持连接池和异步操作
engine = create_async_engine(
    settings.database_url, 
    echo=False  # 生产环境关闭 SQL 日志输出 (Disable SQL logging in production)
)

# 创建异步会话工厂 (Create Async Session Factory)
# 配置会话不在提交后过期，保持对象状态以便后续访问
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False  # 提交后不过期对象，便于访问已保存的数据 (Don't expire objects after commit)
)


class Base(DeclarativeBase):
    """
    ORM 模型基类 (ORM Model Base Class)
    
    SQLAlchemy 2.0 的声明式基类，所有数据模型都继承此类。
    提供表映射、字段定义和关系管理的基础功能。
    
    SQLAlchemy 2.0 declarative base class that all data models inherit from.
    Provides basic functionality for table mapping, field definition, and relationship management.
    """
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖项：获取数据库会话 (FastAPI Dependency: Get Database Session)
    
    为 API 路由提供数据库会话的依赖注入函数。
    使用异步上下文管理器确保会话在请求结束后正确关闭，防止连接泄漏。
    
    Dependency injection function that provides database sessions for API routes.
    Uses async context manager to ensure sessions are properly closed after requests,
    preventing connection leaks.
    
    Yields:
        AsyncSession: 异步数据库会话实例 (Async database session instance)
    """
    async with async_session() as session:
        yield session
