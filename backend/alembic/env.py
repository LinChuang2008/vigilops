"""Alembic 数据库迁移环境配置。

配置异步 SQLAlchemy 引擎，支持离线和在线两种迁移模式。
在线模式通过 asyncio 运行异步迁移。
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base
from app.models import User  # noqa: F401  确保模型被导入以便 autogenerate 检测

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 迁移目标元数据，Alembic 据此生成迁移脚本
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移，仅生成 SQL 语句而不连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """在同步连接上执行迁移（供 run_sync 回调使用）。"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """创建异步引擎并在异步连接上执行迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """在线模式运行迁移，通过 asyncio 驱动异步引擎。"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
