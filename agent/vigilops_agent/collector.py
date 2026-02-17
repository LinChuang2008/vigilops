"""
系统指标采集模块。

使用 psutil 采集 CPU、内存、磁盘、网络等系统指标，
支持网络速率计算和丢包率统计。
"""
import logging
import platform
import time
from typing import Optional

import psutil

logger = logging.getLogger(__name__)

# 模块级状态，用于网络速率的差值计算
_prev_net: Optional[dict] = None
_prev_time: Optional[float] = None


def collect_system_info() -> dict:
    """采集静态系统信息（主机名、OS、CPU 核数、总内存等）。"""
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
    """采集当前系统运行指标。

    包括 CPU 使用率、负载、内存、磁盘、网络流量及丢包率。
    网络速率通过与上次采集的差值计算得出。
    """
    cpu_percent = psutil.cpu_percent(interval=1)

    try:
        load1, load5, load15 = psutil.getloadavg()
    except (AttributeError, OSError):
        load1 = load5 = load15 = 0.0

    mem = psutil.virtual_memory()

    # 磁盘 — 使用根分区
    try:
        disk = psutil.disk_usage("/")
        disk_used_mb = int(disk.used / (1024 * 1024))
        disk_total_mb = int(disk.total / (1024 * 1024))
        disk_percent = disk.percent
    except Exception:
        disk_used_mb = disk_total_mb = 0
        disk_percent = 0.0

    # 网络 — 累计计数器 + 速率计算
    global _prev_net, _prev_time
    net = psutil.net_io_counters()
    now = time.monotonic()

    net_send_rate_kb = 0.0
    net_recv_rate_kb = 0.0
    net_packet_loss_rate = 0.0

    # 与上次采集对比，计算每秒发送/接收速率（KB/s）
    if _prev_net is not None and _prev_time is not None:
        dt = now - _prev_time
        if dt > 0:
            net_send_rate_kb = round((net.bytes_sent - _prev_net["bytes_sent"]) / 1024 / dt, 2)
            net_recv_rate_kb = round((net.bytes_recv - _prev_net["bytes_recv"]) / 1024 / dt, 2)

    # 丢包率：丢弃包数 / 总包数（百分比）
    total_in = net.packets_recv + net.dropin
    total_out = net.packets_sent + net.dropout
    total_packets = total_in + total_out
    if total_packets > 0:
        net_packet_loss_rate = round((net.dropin + net.dropout) / total_packets * 100, 4)

    # 保存本次采集数据，供下次计算差值
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
