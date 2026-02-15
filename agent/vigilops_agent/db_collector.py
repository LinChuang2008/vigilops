"""F059/F060: Database metrics collection for PostgreSQL and MySQL."""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from vigilops_agent.config import DatabaseMonitorConfig

logger = logging.getLogger(__name__)


def collect_postgres_metrics(cfg: DatabaseMonitorConfig) -> Optional[Dict]:
    """Collect PostgreSQL metrics using psycopg2."""
    try:
        import psycopg2  # type: ignore
    except ImportError:
        logger.warning("psycopg2 not installed, skipping PostgreSQL collection for %s", cfg.name)
        return None

    try:
        conn = psycopg2.connect(
            host=cfg.host,
            port=cfg.port,
            dbname=cfg.database,
            user=cfg.username,
            password=cfg.password,
            connect_timeout=10,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Total connections
        cur.execute("SELECT count(*) FROM pg_stat_activity;")
        connections_total = cur.fetchone()[0]

        # Active connections
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
        connections_active = cur.fetchone()[0]

        # Database size
        cur.execute("SELECT pg_database_size(current_database());")
        database_size_bytes = cur.fetchone()[0]
        database_size_mb = round(database_size_bytes / (1024 * 1024), 2)

        # Slow queries (pg_stat_statements if available)
        slow_queries = 0
        try:
            cur.execute("SELECT count(*) FROM pg_stat_statements WHERE mean_exec_time > 1000;")
            slow_queries = cur.fetchone()[0]
        except Exception:
            pass

        # Table count
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        tables_count = cur.fetchone()[0]

        # Transaction stats
        cur.execute("SELECT xact_commit, xact_rollback FROM pg_stat_database WHERE datname = current_database();")
        row = cur.fetchone()
        xact_commit = row[0] if row else 0
        xact_rollback = row[1] if row else 0

        cur.close()
        conn.close()

        return {
            "db_name": cfg.name or cfg.database,
            "db_type": "postgres",
            "connections_total": connections_total,
            "connections_active": connections_active,
            "database_size_mb": database_size_mb,
            "slow_queries": slow_queries,
            "tables_count": tables_count,
            "transactions_committed": xact_commit,
            "transactions_rolled_back": xact_rollback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("PostgreSQL collection failed for %s: %s", cfg.name, e)
        return None


def collect_mysql_metrics(cfg: DatabaseMonitorConfig) -> Optional[Dict]:
    """Collect MySQL metrics using pymysql."""
    try:
        import pymysql  # type: ignore
    except ImportError:
        logger.warning("pymysql not installed, skipping MySQL collection for %s", cfg.name)
        return None

    try:
        conn = pymysql.connect(
            host=cfg.host,
            port=cfg.port,
            database=cfg.database,
            user=cfg.username,
            password=cfg.password,
            connect_timeout=10,
        )
        cur = conn.cursor()

        def _status_val(variable_name: str) -> int:
            cur.execute("SHOW STATUS LIKE %s;", (variable_name,))
            row = cur.fetchone()
            return int(row[1]) if row else 0

        connections_total = _status_val("Threads_connected")
        connections_active = _status_val("Threads_running")
        slow_queries = _status_val("Slow_queries")
        queries = _status_val("Queries")

        # Database size
        cur.execute(
            "SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = DATABASE();"
        )
        row = cur.fetchone()
        size_bytes = row[0] if row and row[0] else 0
        database_size_mb = round(size_bytes / (1024 * 1024), 2)

        # Table count
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = DATABASE();")
        tables_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {
            "db_name": cfg.name or cfg.database,
            "db_type": "mysql",
            "connections_total": connections_total,
            "connections_active": connections_active,
            "database_size_mb": database_size_mb,
            "slow_queries": slow_queries,
            "tables_count": tables_count,
            "transactions_committed": 0,
            "transactions_rolled_back": 0,
            "qps": queries,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("MySQL collection failed for %s: %s", cfg.name, e)
        return None


def collect_db_metrics(cfg: DatabaseMonitorConfig) -> Optional[Dict]:
    """Collect metrics based on database type."""
    if cfg.type == "postgres":
        return collect_postgres_metrics(cfg)
    elif cfg.type == "mysql":
        return collect_mysql_metrics(cfg)
    else:
        logger.warning("Unsupported database type: %s", cfg.type)
        return None
