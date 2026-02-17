"""
数据库指标采集模块。

支持 PostgreSQL、MySQL 和 Oracle 三种数据库的指标采集，
包括连接数、数据库大小、慢查询、事务统计等。
Oracle 通过 docker exec + sqlplus 方式采集。
"""
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional

from vigilops_agent.config import DatabaseMonitorConfig

logger = logging.getLogger(__name__)


def collect_postgres_metrics(cfg: DatabaseMonitorConfig) -> Optional[Dict]:
    """采集 PostgreSQL 指标。

    通过 psycopg2 连接数据库，查询连接数、库大小、慢查询、表数量、事务统计等。

    Returns:
        指标字典，采集失败返回 None。
    """
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

        # 总连接数
        cur.execute("SELECT count(*) FROM pg_stat_activity;")
        connections_total = cur.fetchone()[0]

        # 活跃连接数
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
        connections_active = cur.fetchone()[0]

        # 数据库大小
        cur.execute("SELECT pg_database_size(current_database());")
        database_size_bytes = cur.fetchone()[0]
        database_size_mb = round(database_size_bytes / (1024 * 1024), 2)

        # 慢查询数（依赖 pg_stat_statements 扩展）
        slow_queries = 0
        try:
            cur.execute("SELECT count(*) FROM pg_stat_statements WHERE mean_exec_time > 1000;")
            slow_queries = cur.fetchone()[0]
        except Exception:
            pass

        # 公共 schema 中的表数量
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        tables_count = cur.fetchone()[0]

        # 事务提交/回滚统计
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
    """采集 MySQL 指标。

    通过 pymysql 连接数据库，查询连接数、慢查询、库大小、表数量等。

    Returns:
        指标字典，采集失败返回 None。
    """
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
            """查询 SHOW STATUS 中指定变量的值。"""
            cur.execute("SHOW STATUS LIKE %s;", (variable_name,))
            row = cur.fetchone()
            return int(row[1]) if row else 0

        connections_total = _status_val("Threads_connected")
        connections_active = _status_val("Threads_running")
        slow_queries = _status_val("Slow_queries")
        queries = _status_val("Queries")

        # 数据库大小
        cur.execute(
            "SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = DATABASE();"
        )
        row = cur.fetchone()
        size_bytes = row[0] if row and row[0] else 0
        database_size_mb = round(size_bytes / (1024 * 1024), 2)

        # 表数量
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
    """采集 Oracle 指标。

    通过 docker exec 在容器内执行 sqlplus 命令，查询会话数、库大小、
    表空间使用率、慢查询等指标。

    Returns:
        指标字典，采集失败返回 None。
    """
    container = cfg.container_name
    if not container:
        logger.warning("Oracle monitoring requires container_name for %s", cfg.name)
        return None

    # 构造 Oracle 环境变量设置命令
    if cfg.oracle_home:
        oracle_env = (
            f"export ORACLE_HOME={cfg.oracle_home}; "
            f"export ORACLE_SID={cfg.oracle_sid}; "
            f"export PATH=$ORACLE_HOME/bin:$PATH; "
        )
    else:
        oracle_env = "source /home/oracle/.bash_profile 2>/dev/null; "

    # 基础指标查询 SQL
    sql_script = (
        "SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF\n"
        "SELECT 'TOTAL_SESSIONS=' || count(*) FROM v$session;\n"
        "SELECT 'ACTIVE_SESSIONS=' || count(*) FROM v$session WHERE status = 'ACTIVE';\n"
        "SELECT 'DB_SIZE_MB=' || ROUND(SUM(bytes)/1024/1024, 2) FROM dba_data_files;\n"
        "SELECT 'TABLESPACE_USED_PCT=' || ROUND(MAX(used_percent), 2) FROM dba_tablespace_usage_metrics;\n"
        "SELECT 'SLOW_QUERIES=' || count(*) FROM v$sql WHERE elapsed_time/GREATEST(executions,1) > 5000000 AND executions > 0;\n"
        "EXIT;\n"
    )

    # 用 printf %s 避免 shell 对 $session/$sql 等变量的展开
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

    # 解析 KEY=VALUE 格式的输出
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
        """安全转换为整数。"""
        try:
            return int(values.get(k, str(default)))
        except (ValueError, TypeError):
            return default

    def _float(k: str, default: float = 0.0) -> float:
        """安全转换为浮点数。"""
        try:
            return float(values.get(k, str(default)))
        except (ValueError, TypeError):
            return default

    # 采集 Top 10 慢查询详情
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
    """采集 Oracle v$sql 中平均执行时间最长的 Top 10 慢查询。"""
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

    # 解析 "|||" 分隔的输出行
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
    """根据数据库类型分派执行对应的指标采集。"""
    if cfg.type == "postgres":
        return collect_postgres_metrics(cfg)
    elif cfg.type == "mysql":
        return collect_mysql_metrics(cfg)
    elif cfg.type == "oracle":
        return collect_oracle_metrics(cfg)
    else:
        logger.warning("Unsupported database type: %s", cfg.type)
        return None
