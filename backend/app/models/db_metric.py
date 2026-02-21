"""
数据库监控模型 (Database Monitoring Model)

定义被监控数据库及其性能指标的表结构，支持 PostgreSQL、MySQL、Oracle 数据库的监控。
包含数据库基本信息、状态管理和详细的性能指标采集，为数据库运维提供全面的监控数据。

Defines table structures for monitored databases and their performance metrics,
supporting PostgreSQL, MySQL, and Oracle database monitoring.
Includes database basic information, status management, and detailed performance metrics collection.
"""
from datetime import datetime

from sqlalchemy import Integer, Float, BigInteger, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MonitoredDatabase(Base):
    """
    被监控数据库表 (Monitored Database Table)
    
    记录系统中需要监控的数据库实例的基本信息和当前状态。
    支持多种数据库类型，并维护数据库的健康状态和慢查询详情等信息。
    
    Table for recording basic information and current status of database instances
    that need to be monitored in the system. Supports multiple database types
    and maintains database health status and slow query details.
    """
    __tablename__ = "monitored_databases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id"), index=True, nullable=False)  # 所属主机 ID (Host ID)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 数据库实例名称 (Database Instance Name)
    db_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 数据库类型：postgres/mysql/oracle (Database Type)
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # 健康状态：健康/警告/严重/未知 (Health Status: healthy/warning/critical/unknown)
    slow_queries_detail = mapped_column(JSON, nullable=True)  # 慢查询 Top 10 详情 JSON 数据 (Slow Queries Top 10 Details)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 创建时间 (Creation Time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 更新时间 (Update Time)


class DbMetric(Base):
    """
    数据库指标表 (Database Metric Table)
    
    存储 Agent 定期上报的数据库性能指标数据，包含连接数、查询性能、事务统计等。
    为数据库监控和告警提供历史数据支持，支持性能趋势分析和异常检测。
    
    Table for storing database performance metric data regularly reported by agents,
    including connection counts, query performance, transaction statistics, etc.
    Provides historical data support for database monitoring and alerting.
    """
    __tablename__ = "db_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # 主键 ID (Primary Key ID)
    database_id: Mapped[int] = mapped_column(Integer, ForeignKey("monitored_databases.id"), index=True, nullable=False)  # 数据库 ID (Database ID)
    connections_total: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 总连接数 (Total Connections)
    connections_active: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 活跃连接数 (Active Connections)
    database_size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)  # 数据库大小 MB (Database Size in MB)
    slow_queries: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 慢查询数量 (Slow Query Count)
    tables_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 数据库表数量 (Table Count)
    transactions_committed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 已提交事务数 (Committed Transactions)
    transactions_rolled_back: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 已回滚事务数 (Rolled Back Transactions)
    qps: Mapped[float | None] = mapped_column(Float, nullable=True)  # 每秒查询数 (Queries Per Second)
    tablespace_used_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # 表空间使用率百分比 (Tablespace Used Percentage)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)  # 记录时间 (Record Time)
