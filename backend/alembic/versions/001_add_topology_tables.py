"""add topology tables (servers, service_groups, server_services, nginx_upstreams)

Revision ID: 001_topology
Revises:
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_topology"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # servers 表
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("hostname", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # service_groups 表
    op.create_table(
        "service_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # server_services 表
    op.create_table(
        "server_services",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("server_id", sa.Integer(), nullable=False, index=True),
        sa.Column("group_id", sa.Integer(), nullable=False, index=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("cpu_percent", sa.Float(), server_default="0"),
        sa.Column("mem_mb", sa.Float(), server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("server_id", "group_id", "port", name="uq_server_service_port"),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["service_groups.id"], ondelete="CASCADE"),
    )

    # nginx_upstreams 表
    op.create_table(
        "nginx_upstreams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("server_id", sa.Integer(), nullable=False, index=True),
        sa.Column("upstream_name", sa.String(255), nullable=False, index=True),
        sa.Column("backend_address", sa.String(255), nullable=False),
        sa.Column("weight", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="up"),
        sa.Column("parsed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("nginx_upstreams")
    op.drop_table("server_services")
    op.drop_table("service_groups")
    op.drop_table("servers")
