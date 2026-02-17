"""
数据库连接模块

创建 SQLAlchemy 异步引擎和会话工厂，提供数据库会话依赖注入。
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 创建异步数据库引擎
engine = create_async_engine(settings.database_url, echo=False)
# 创建异步会话工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 模型基类，所有模型继承此类。"""
    pass


async def get_db():
    """FastAPI 依赖项：获取数据库会话，请求结束后自动关闭。"""
    async with async_session() as session:
        yield session
