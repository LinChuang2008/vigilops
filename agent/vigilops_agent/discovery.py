"""Auto-discover services from Docker containers and listening ports."""
import json
import logging
import shutil
import subprocess
from typing import List

from vigilops_agent.config import ServiceCheckConfig

logger = logging.getLogger(__name__)

# Common HTTP ports for auto-detecting check type
HTTP_PORTS = {80, 443, 8080, 8000, 8001, 8443, 3000, 3001, 5000, 9090,
              8093, 8123, 8848, 13000, 15672, 18000, 18123, 48080, 48848}


def discover_docker_services(interval: int = 30) -> List[ServiceCheckConfig]:
    """Discover services from running Docker containers with published ports."""
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

        # Parse published ports: "0.0.0.0:8001->8000/tcp, ..."
        for mapping in ports_str.split(","):
            mapping = mapping.strip()
            if "->" not in mapping:
                continue
            try:
                host_part, container_part = mapping.split("->")
                # host_part like "0.0.0.0:8001" or "[::]:8001"
                if ":" in host_part:
                    host_port = int(host_part.rsplit(":", 1)[1])
                else:
                    continue
                # Skip IPv6 duplicates
                if host_part.startswith("[::]:"):
                    continue
            except (ValueError, IndexError):
                continue

            # Determine check type
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
    return len([l for l in stdout.strip().splitlines() if l.strip()])


def discover_listening_ports(interval: int = 30) -> List[ServiceCheckConfig]:
    """Discover non-Docker services listening on TCP ports via ss/netstat."""
    # This is a lighter-weight fallback for non-Docker hosts
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

    # For now, Docker discovery is primary. Port discovery can be added later.
    return []
