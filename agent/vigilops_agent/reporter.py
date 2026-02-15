"""Metrics reporter - sends data to VigilOps Server."""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from vigilops_agent import __version__
from vigilops_agent.collector import collect_system_info, collect_metrics
from vigilops_agent.checker import run_check
from vigilops_agent.config import AgentConfig, ServiceCheckConfig, DatabaseMonitorConfig
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class AgentReporter:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.host_id: Optional[int] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._service_ids: Dict[str, int] = {}  # svc name -> service_id

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.server.token}"}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.server.url,
                headers=self._headers(),
                timeout=30,
            )
        return self._client

    def _get_local_ip(self) -> str:
        """Get the host's primary IP address (public > private > loopback)."""
        import socket

        # 1) Try public IP via external services (for cloud VMs)
        for url in [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "http://checkip.amazonaws.com",
        ]:
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=3) as resp:
                    ip = resp.read().decode().strip()
                    if ip and ip != "127.0.0.1":
                        return ip
            except Exception:
                continue

        # 2) Fallback: UDP socket trick to get LAN IP
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.config.server.url)
            host = parsed.hostname or "10.211.55.2"
            port = parsed.port or 80
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((host, port))
            ip = s.getsockname()[0]
            s.close()
            if ip and ip != "127.0.0.1":
                return ip
        except Exception:
            pass

        return ""

    async def register(self):
        """Register this agent with the server."""
        info = collect_system_info()
        payload = {
            "hostname": self.config.host.name or info["hostname"],
            "ip_address": self._get_local_ip(),
            "os": info["os"],
            "os_version": info["os_version"],
            "arch": info["arch"],
            "cpu_cores": info["cpu_cores"],
            "memory_total_mb": info["memory_total_mb"],
            "agent_version": __version__,
            "tags": {t: True for t in self.config.host.tags} if self.config.host.tags else None,
        }
        client = await self._get_client()
        resp = await client.post("/api/v1/agent/register", json=payload)
        resp.raise_for_status()
        data = resp.json()
        self.host_id = data["host_id"]
        logger.info(f"Registered as host_id={self.host_id} (created={data['created']})")

    async def heartbeat(self):
        """Send heartbeat."""
        if not self.host_id:
            return
        client = await self._get_client()
        resp = await client.post("/api/v1/agent/heartbeat", json={"host_id": self.host_id})
        resp.raise_for_status()

    async def report_metrics(self):
        """Collect and report metrics."""
        if not self.host_id:
            return
        metrics = collect_metrics()
        metrics["host_id"] = self.host_id
        metrics["timestamp"] = datetime.now(timezone.utc).isoformat()
        client = await self._get_client()
        resp = await client.post("/api/v1/agent/metrics", json=metrics)
        resp.raise_for_status()
        logger.debug(f"Metrics reported: cpu={metrics['cpu_percent']}% mem={metrics['memory_percent']}%")

    async def register_services(self):
        """Register configured services with the server."""
        client = await self._get_client()
        for svc in self.config.services:
            try:
                payload = {
                    "name": svc.name,
                    "type": svc.type,
                    "target": svc.url or f"{svc.host}:{svc.port}",
                    "host_id": self.host_id,
                    "check_interval": svc.interval,
                    "timeout": svc.timeout,
                }
                resp = await client.post("/api/v1/agent/services/register", json=payload)
                resp.raise_for_status()
                data = resp.json()
                self._service_ids[svc.name] = data["service_id"]
                logger.info(f"Service registered: {svc.name} -> id={data['service_id']}")
            except Exception as e:
                logger.warning(f"Failed to register service {svc.name}: {e}")

    async def report_service_check(self, svc: ServiceCheckConfig, result: dict):
        """Report a service check result."""
        service_id = self._service_ids.get(svc.name)
        if not service_id:
            return
        client = await self._get_client()
        payload = {
            "service_id": service_id,
            "status": result["status"],
            "response_time_ms": result["response_time_ms"],
            "status_code": result["status_code"],
            "error": result["error"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = await client.post("/api/v1/agent/services", json=payload)
        resp.raise_for_status()
        logger.debug(f"Service check reported: {svc.name} = {result['status']}")

    async def report_logs(self, logs: List[Dict]) -> bool:
        """Report a batch of log entries. Returns True on success."""
        if not self.host_id or not logs:
            return False
        try:
            client = await self._get_client()
            resp = await client.post("/api/v1/agent/logs", json={"logs": logs})
            resp.raise_for_status()
            logger.debug(f"Reported {len(logs)} log entries")
            return True
        except Exception as e:
            logger.warning(f"Log report failed ({len(logs)} entries): {e}")
            return False

    async def report_db_metrics(self, metrics: dict):
        """Report database metrics to backend."""
        if not self.host_id:
            return
        metrics["host_id"] = self.host_id
        client = await self._get_client()
        resp = await client.post("/api/v1/agent/db-metrics", json=metrics)
        resp.raise_for_status()
        logger.debug("DB metrics reported: %s", metrics.get("db_name"))

    async def _db_monitor_loop(self, db_config: DatabaseMonitorConfig):
        """Periodic database metrics collection loop."""
        from vigilops_agent.db_collector import collect_db_metrics
        while True:
            try:
                metrics = collect_db_metrics(db_config)
                if metrics:
                    await self.report_db_metrics(metrics)
            except Exception as e:
                logger.warning("DB monitor failed for %s: %s", db_config.name, e)
            await asyncio.sleep(db_config.interval)

    async def _service_check_loop(self, svc: ServiceCheckConfig):
        """Run periodic checks for a single service."""
        while True:
            try:
                result = await run_check(svc)
                await self.report_service_check(svc, result)
            except Exception as e:
                logger.warning(f"Service check failed for {svc.name}: {e}")
            await asyncio.sleep(svc.interval)

    async def _heartbeat_loop(self):
        """Heartbeat every 60s."""
        while True:
            try:
                await self.heartbeat()
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
            await asyncio.sleep(60)

    async def _metrics_loop(self):
        """Metrics collection loop."""
        interval = self.config.metrics.interval
        while True:
            try:
                await self.report_metrics()
            except Exception as e:
                logger.warning(f"Metrics report failed: {e}")
            await asyncio.sleep(interval)

    async def start(self):
        """Start the agent: register, then run heartbeat + metrics loops."""
        # Register with retry
        for attempt in range(10):
            try:
                await self.register()
                break
            except Exception as e:
                wait = min(2 ** attempt, 60)
                logger.warning(f"Registration failed (attempt {attempt + 1}): {e}. Retry in {wait}s")
                await asyncio.sleep(wait)
        else:
            raise RuntimeError("Failed to register after 10 attempts")

        # Auto-discover services
        if self.config.discovery.docker:
            from vigilops_agent.discovery import discover_docker_services
            discovered = discover_docker_services(interval=self.config.discovery.interval)
            # Merge: skip discovered services whose name already in manual config
            manual_names = {s.name for s in self.config.services}
            for svc in discovered:
                if svc.name not in manual_names:
                    self.config.services.append(svc)
            if discovered:
                logger.info(f"Auto-discovered {len(discovered)} services, "
                            f"total after merge: {len(self.config.services)}")

        # Register services
        if self.config.services:
            await self.register_services()

        # Log collection
        log_sources = list(self.config.log_sources)
        if self.config.discovery.docker:
            from vigilops_agent.discovery import discover_docker_log_sources
            docker_logs = discover_docker_log_sources()
            existing_paths = {s.path for s in log_sources}
            for src in docker_logs:
                if src.path not in existing_paths:
                    log_sources.append(src)
            if docker_logs:
                logger.info(f"Auto-discovered {len(docker_logs)} Docker log sources")

        # Run loops concurrently
        tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._metrics_loop()),
        ]
        for svc in self.config.services:
            if svc.name in self._service_ids:
                tasks.append(asyncio.create_task(self._service_check_loop(svc)))

        # Database monitoring loops
        for db_config in self.config.databases:
            tasks.append(asyncio.create_task(self._db_monitor_loop(db_config)))
        if self.config.databases:
            logger.info("Database monitoring started for %d database(s)", len(self.config.databases))

        if log_sources:
            from vigilops_agent.log_collector import LogCollector
            collector = LogCollector(self.host_id, log_sources, self.report_logs)
            log_tasks = await collector.start()
            tasks.extend(log_tasks)

        logger.info("Agent running. Press Ctrl+C to stop.")
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            if self._client:
                await self._client.aclose()
