"""Metrics reporter - sends data to VigilOps Server."""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from vigilops_agent import __version__
from vigilops_agent.collector import collect_system_info, collect_metrics
from vigilops_agent.config import AgentConfig

logger = logging.getLogger(__name__)


class AgentReporter:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.host_id: int | None = None
        self._client: httpx.AsyncClient | None = None

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

    async def register(self):
        """Register this agent with the server."""
        info = collect_system_info()
        payload = {
            "hostname": self.config.host.name or info["hostname"],
            "ip_address": None,
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

        # Run loops concurrently
        tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._metrics_loop()),
        ]

        logger.info("Agent running. Press Ctrl+C to stop.")
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            if self._client:
                await self._client.aclose()
