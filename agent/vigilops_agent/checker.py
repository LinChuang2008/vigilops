"""HTTP/TCP service health checker."""
import asyncio
import logging
import socket
import time

import httpx

from vigilops_agent.config import ServiceCheckConfig

logger = logging.getLogger(__name__)


async def check_http(svc: ServiceCheckConfig) -> dict:
    """Perform HTTP health check."""
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=svc.timeout) as client:
            resp = await client.get(svc.url)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        status = "up" if 200 <= resp.status_code < 500 else "down"
        return {
            "status": status,
            "response_time_ms": elapsed_ms,
            "status_code": resp.status_code,
            "error": None,
        }
    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "status": "down",
            "response_time_ms": elapsed_ms,
            "status_code": None,
            "error": str(e)[:500],
        }


async def check_tcp(svc: ServiceCheckConfig) -> dict:
    """Perform TCP connection check."""
    host = svc.host or "localhost"
    port = svc.port
    if not port:
        return {"status": "down", "response_time_ms": 0, "status_code": None, "error": "No port configured"}

    start = time.monotonic()
    try:
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, _tcp_connect, host, port, svc.timeout),
            timeout=svc.timeout,
        )
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {"status": "up", "response_time_ms": elapsed_ms, "status_code": None, "error": None}
    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {"status": "down", "response_time_ms": elapsed_ms, "status_code": None, "error": str(e)[:500]}


def _tcp_connect(host: str, port: int, timeout: int):
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.close()


async def run_check(svc: ServiceCheckConfig) -> dict:
    """Run the appropriate check based on service type."""
    if svc.type == "http":
        return await check_http(svc)
    elif svc.type == "tcp":
        return await check_tcp(svc)
    else:
        return {"status": "down", "response_time_ms": 0, "status_code": None, "error": f"Unknown type: {svc.type}"}
