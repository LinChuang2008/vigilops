"""F062: Database monitoring models."""
from datetime import datetime

from sqlalchemy import Integer, Float, BigInteger, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MonitoredDatabase(Base):
    __tablename__ = "monitored_databases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(Integer, ForeignKey("hosts.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_type: Mapped[str] = mapped_column(String(20), nullable=False)  # postgres / mysql
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # healthy/warning/critical/unknown
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DbMetric(Base):
    __tablename__ = "db_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    database_id: Mapped[int] = mapped_column(Integer, ForeignKey("monitored_databases.id"), index=True, nullable=False)
    connections_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connections_active: Mapped[int | None] = mapped_column(Integer, nullable=True)
    database_size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    slow_queries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tables_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transactions_committed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transactions_rolled_back: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    qps: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
