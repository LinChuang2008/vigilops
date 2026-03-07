"""add name_en to alert_rules and title_en to alerts

Revision ID: 003_add_en_fields
Revises: 002_metrics_server_id
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_add_en_fields"
down_revision: Union[str, None] = "002_metrics_server_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("name_en", sa.String(255), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("title_en", sa.String(500), nullable=True),
    )
    # Populate English names for built-in rules
    op.execute("""
        UPDATE alert_rules SET name_en = CASE name
            WHEN 'CPU 使用率过高' THEN 'High CPU Usage'
            WHEN '内存使用率过高' THEN 'High Memory Usage'
            WHEN '磁盘使用率过高' THEN 'High Disk Usage'
            WHEN '主机离线' THEN 'Host Offline'
            WHEN '服务不可用' THEN 'Service Unavailable'
            ELSE NULL
        END
        WHERE is_builtin = TRUE
    """)


def downgrade() -> None:
    op.drop_column("alert_rules", "name_en")
    op.drop_column("alerts", "title_en")
