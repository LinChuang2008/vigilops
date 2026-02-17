"""
数据库监控模型

定义被监控数据库及其性能指标的表结构，支持 PostgreSQL、MySQL、Oracle。
"""
from datetime import datetime

from sqlalchemy import Integer, Float, BigInteger, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MonitoredDatabase(Base):
    """被监控数据库表，记录数据库基本信息和状态。"""
    __tablename__ = "monitored_databases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_type: Mapped[str] = mapped_column(String(20), nullable=False)  # postgres / mysql / oracle
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # healthy / warning / critical / unknown
    slow_queries_detail = mapped_column(JSON, nullable=True)  # Oracle 慢查询 Top 10 详情
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DbMetric(Base):
    """数据库指标表，存储 Agent 上报的数据库性能数据。"""
    __tablename__ = "db_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    database_id: Mapped[int] = mapped_column(Integer, ForeignKey("monitored_databases.id"), index=True, nullable=False)
    connections_total: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 总连接数
    connections_active: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 活跃连接数
    database_size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)  # 数据库大小(MB)
    slow_queries: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 慢查询数量
    tables_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 表数量
    transactions_committed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 已提交事务
    transactions_rolled_back: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 已回滚事务
    qps: Mapped[float | None] = mapped_column(Float, nullable=True)  # 每秒查询数
    tablespace_used_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # 表空间使用率(%)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
