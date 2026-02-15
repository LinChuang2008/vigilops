"""System metrics collector using psutil."""
import logging
import platform
import time

import psutil

logger = logging.getLogger(__name__)

# Module-level state for rate calculation
_prev_net: dict | None = None
_prev_time: float | None = None


def collect_system_info() -> dict:
    """Collect static system information."""
    uname = platform.uname()
    mem = psutil.virtual_memory()
    return {
        "hostname": platform.node(),
        "os": uname.system,
        "os_version": uname.release,
        "arch": uname.machine,
        "cpu_cores": psutil.cpu_count(logical=True),
        "memory_total_mb": int(mem.total / (1024 * 1024)),
    }


def collect_metrics() -> dict:
    """Collect current system metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)

    try:
        load1, load5, load15 = psutil.getloadavg()
    except (AttributeError, OSError):
        load1 = load5 = load15 = 0.0

    mem = psutil.virtual_memory()

    # Disk — use root partition
    try:
        disk = psutil.disk_usage("/")
        disk_used_mb = int(disk.used / (1024 * 1024))
        disk_total_mb = int(disk.total / (1024 * 1024))
        disk_percent = disk.percent
    except Exception:
        disk_used_mb = disk_total_mb = 0
        disk_percent = 0.0

    # Network — cumulative counters + rate calculation
    global _prev_net, _prev_time
    net = psutil.net_io_counters()
    now = time.monotonic()

    net_send_rate_kb = 0.0
    net_recv_rate_kb = 0.0
    net_packet_loss_rate = 0.0

    if _prev_net is not None and _prev_time is not None:
        dt = now - _prev_time
        if dt > 0:
            net_send_rate_kb = round((net.bytes_sent - _prev_net["bytes_sent"]) / 1024 / dt, 2)
            net_recv_rate_kb = round((net.bytes_recv - _prev_net["bytes_recv"]) / 1024 / dt, 2)

    # Packet loss rate: dropped / (received + dropped) as percentage
    total_in = net.packets_recv + net.dropin
    total_out = net.packets_sent + net.dropout
    total_packets = total_in + total_out
    if total_packets > 0:
        net_packet_loss_rate = round((net.dropin + net.dropout) / total_packets * 100, 4)

    _prev_net = {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
    }
    _prev_time = now

    return {
        "cpu_percent": round(cpu_percent, 1),
        "cpu_load_1": round(load1, 2),
        "cpu_load_5": round(load5, 2),
        "cpu_load_15": round(load15, 2),
        "memory_used_mb": int(mem.used / (1024 * 1024)),
        "memory_percent": round(mem.percent, 1),
        "disk_used_mb": disk_used_mb,
        "disk_total_mb": disk_total_mb,
        "disk_percent": round(disk_percent, 1),
        "net_bytes_sent": net.bytes_sent,
        "net_bytes_recv": net.bytes_recv,
        "net_send_rate_kb": net_send_rate_kb,
        "net_recv_rate_kb": net_recv_rate_kb,
        "net_packet_loss_rate": net_packet_loss_rate,
    }
