"""System metrics collector using psutil."""
import logging
import platform

import psutil

logger = logging.getLogger(__name__)


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

    # Network — cumulative counters
    net = psutil.net_io_counters()

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
    }
