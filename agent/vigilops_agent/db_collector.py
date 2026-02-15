"""F059/F060: Database metrics collection for PostgreSQL, MySQL, and Oracle."""
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional

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


def collect_oracle_metrics(cfg: DatabaseMonitorConfig) -> Optional[Dict]:
    """Collect Oracle metrics via docker exec + sqlplus."""
    container = cfg.container_name
    if not container:
        logger.warning("Oracle monitoring requires container_name for %s", cfg.name)
        return None

    if cfg.oracle_home:
        oracle_env = (
            f"export ORACLE_HOME={cfg.oracle_home}; "
            f"export ORACLE_SID={cfg.oracle_sid}; "
            f"export PATH=$ORACLE_HOME/bin:$PATH; "
        )
    else:
        oracle_env = "source /home/oracle/.bash_profile 2>/dev/null; "

    # Basic metrics SQL
    sql_script = (
        "SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF\n"
        "SELECT 'TOTAL_SESSIONS=' || count(*) FROM v$session;\n"
        "SELECT 'ACTIVE_SESSIONS=' || count(*) FROM v$session WHERE status = 'ACTIVE';\n"
        "SELECT 'DB_SIZE_MB=' || ROUND(SUM(bytes)/1024/1024, 2) FROM dba_data_files;\n"
        "SELECT 'TABLESPACE_USED_PCT=' || ROUND(MAX(used_percent), 2) FROM dba_tablespace_usage_metrics;\n"
        "SELECT 'SLOW_QUERIES=' || count(*) FROM v$sql WHERE elapsed_time/GREATEST(executions,1) > 5000000 AND executions > 0;\n"
        "EXIT;\n"
    )

    # Use printf with %s to avoid shell variable expansion of $session/$sql
    bash_cmd = oracle_env + "printf '%s' '" + sql_script.replace("'", "'\\''") + "' | sqlplus -s / as sysdba"
    cmd = ["docker", "exec", container, "bash", "-c", bash_cmd]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout
    except subprocess.TimeoutExpired:
        logger.error("Oracle sqlplus timed out for %s", cfg.name)
        return None
    except Exception as e:
        logger.error("Oracle collection failed for %s: %s", cfg.name, e)
        return None

    # Parse KEY=VALUE pairs
    values = {}  # type: Dict[str, str]
    for line in output.splitlines():
        line = line.strip()
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key in ("TOTAL_SESSIONS", "ACTIVE_SESSIONS", "DB_SIZE_MB", "TABLESPACE_USED_PCT", "SLOW_QUERIES"):
                values[key] = val

    if not values:
        logger.error("Oracle: no metrics parsed from sqlplus output for %s", cfg.name)
        return None

    def _int(k: str, default: int = 0) -> int:
        try:
            return int(values.get(k, str(default)))
        except (ValueError, TypeError):
            return default

    def _float(k: str, default: float = 0.0) -> float:
        try:
            return float(values.get(k, str(default)))
        except (ValueError, TypeError):
            return default

    # Collect slow queries detail
    slow_queries_detail = _collect_oracle_slow_queries(container, oracle_env)

    metrics = {
        "db_name": cfg.name or cfg.database or cfg.oracle_sid,
        "db_type": "oracle",
        "connections_total": _int("TOTAL_SESSIONS"),
        "connections_active": _int("ACTIVE_SESSIONS"),
        "database_size_mb": _float("DB_SIZE_MB"),
        "slow_queries": _int("SLOW_QUERIES"),
        "tables_count": 0,
        "transactions_committed": 0,
        "transactions_rolled_back": 0,
        "tablespace_used_pct": _float("TABLESPACE_USED_PCT"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if slow_queries_detail:
        metrics["slow_queries_detail"] = slow_queries_detail

    return metrics


def _collect_oracle_slow_queries(container: str, oracle_env: str) -> Optional[List[Dict]]:
    """Collect top 10 slow queries from Oracle v$sql."""
    sql = (
        "SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF LINESIZE 500\n"
        "SELECT sql_id || '|||' || ROUND(elapsed_time/executions/1000000, 2) || '|||' || executions || '|||' || SUBSTR(sql_text, 1, 200)\n"
        "FROM (SELECT sql_id, elapsed_time, executions, sql_text\n"
        "      FROM v$sql WHERE executions > 0 ORDER BY elapsed_time/executions DESC)\n"
        "WHERE ROWNUM <= 10;\n"
        "EXIT;\n"
    )
    bash_cmd = oracle_env + "printf '%s' '" + sql.replace("'", "'\\''") + "' | sqlplus -s / as sysdba"
    cmd = ["docker", "exec", container, "bash", "-c", bash_cmd]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout
    except Exception:
        return None

    queries = []  # type: List[Dict]
    for line in output.splitlines():
        line = line.strip()
        if not line or "|||" not in line:
            continue
        parts = line.split("|||", 3)
        if len(parts) < 4:
            continue
        try:
            queries.append({
                "sql_id": parts[0].strip(),
                "avg_seconds": float(parts[1].strip()),
                "executions": int(parts[2].strip()),
                "sql_text": parts[3].strip(),
            })
        except (ValueError, IndexError):
            continue
    return queries if queries else None


def collect_db_metrics(cfg: DatabaseMonitorConfig) -> Optional[Dict]:
    """Collect metrics based on database type."""
    if cfg.type == "postgres":
        return collect_postgres_metrics(cfg)
    elif cfg.type == "mysql":
        return collect_mysql_metrics(cfg)
    elif cfg.type == "oracle":
        return collect_oracle_metrics(cfg)
    else:
        logger.warning("Unsupported database type: %s", cfg.type)
        return None
