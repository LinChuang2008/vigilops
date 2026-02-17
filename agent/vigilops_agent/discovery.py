"""
服务自动发现模块。

通过 Docker API 自动发现运行中的容器及其暴露端口，
生成对应的服务检查配置和日志源配置。
"""
import json
import logging
import shutil
import subprocess
from typing import List

from vigilops_agent.config import LogSourceConfig, ServiceCheckConfig

logger = logging.getLogger(__name__)

# 常见 HTTP 端口集合，用于自动判断检查类型
HTTP_PORTS = {80, 443, 8080, 8000, 8001, 8443, 3000, 3001, 5000, 9090,
              8093, 8123, 8848, 13000, 15672, 18000, 18123, 48080, 48848}


def discover_docker_services(interval: int = 30) -> List[ServiceCheckConfig]:
    """从运行中的 Docker 容器发现服务。

    解析容器的端口映射，根据端口号自动判断使用 HTTP 或 TCP 检查。

    Args:
        interval: 发现的服务默认检查间隔（秒）。

    Returns:
        服务检查配置列表。
    """
    if not shutil.which("docker"):
        logger.debug("Docker not found, skipping container discovery")
        return []

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            logger.warning(f"docker ps failed: {result.stderr.strip()}")
            return []
    except Exception as e:
        logger.warning(f"Docker discovery error: {e}")
        return []

    services = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            container = json.loads(line)
        except json.JSONDecodeError:
            continue

        name = container.get("Names", "").strip()
        ports_str = container.get("Ports", "")
        status = container.get("Status", "")

        if not name or not ports_str:
            continue

        # 解析端口映射，格式如 "0.0.0.0:8001->8000/tcp, ..."
        for mapping in ports_str.split(","):
            mapping = mapping.strip()
            if "->" not in mapping:
                continue
            try:
                host_part, container_part = mapping.split("->")
                if ":" in host_part:
                    host_port = int(host_part.rsplit(":", 1)[1])
                else:
                    continue
                # 跳过 IPv6 重复映射
                if host_part.startswith("[::]:"):
                    continue
            except (ValueError, IndexError):
                continue

            # 根据端口号判断检查类型
            if host_port in HTTP_PORTS:
                svc = ServiceCheckConfig(
                    name=f"{name} (:{host_port})",
                    type="http",
                    url=f"http://localhost:{host_port}",
                    interval=interval,
                )
            else:
                svc = ServiceCheckConfig(
                    name=f"{name} (:{host_port})",
                    type="tcp",
                    host="localhost",
                    port=host_port,
                    interval=interval,
                )
            services.append(svc)

    logger.info(f"Docker discovery: found {len(services)} services from {_count_containers(result.stdout)} containers")
    return services


def _count_containers(stdout: str) -> int:
    """统计 docker ps 输出中的容器数量。"""
    return len([l for l in stdout.strip().splitlines() if l.strip()])


def discover_docker_log_sources() -> List[LogSourceConfig]:
    """从运行中的 Docker 容器发现日志文件路径。

    通过 docker inspect 获取每个容器的 LogPath。

    Returns:
        日志源配置列表。
    """
    if not shutil.which("docker"):
        return []

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
    except Exception as e:
        logger.warning(f"Docker log discovery error: {e}")
        return []

    sources: List[LogSourceConfig] = []
    for name in result.stdout.strip().splitlines():
        name = name.strip()
        if not name:
            continue
        try:
            insp = subprocess.run(
                ["docker", "inspect", "--format", "{{.LogPath}}", name],
                capture_output=True, text=True, timeout=10,
            )
            log_path = insp.stdout.strip()
            if insp.returncode == 0 and log_path and log_path != "<no value>":
                sources.append(LogSourceConfig(
                    path=log_path,
                    service=name,
                    docker=True,
                ))
        except Exception:
            continue

    logger.info(f"Docker log discovery: found {len(sources)} log sources")
    return sources


def discover_listening_ports(interval: int = 30) -> List[ServiceCheckConfig]:
    """通过 ss 命令发现监听中的 TCP 端口服务（备用方案）。

    当前为预留接口，Docker 发现为主要方式。
    """
    if not shutil.which("ss"):
        return []

    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
    except Exception:
        return []

    return []
