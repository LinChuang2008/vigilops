/**
 * 主机监控服务模块
 * 提供主机列表、详情和性能指标的 API 调用
 */
import api from './api';

/** 主机信息 */
export interface Host {
  id: string;
  /** 主机名 */
  hostname: string;
  /** IP 地址 */
  ip_address: string;
  /** 操作系统 */
  os: string;
  /** 运行状态（online / offline / warning） */
  status: string;
  /** 标签（支持对象或数组格式） */
  tags: Record<string, boolean> | string[] | null;
  /** 所属分组 */
  group: string;
  /** 最后心跳时间 */
  last_heartbeat: string | null;
  created_at: string;
  /** 最新性能指标 */
  latest_metrics?: HostMetrics;
}

/** 主机性能指标 */
export interface HostMetrics {
  /** CPU 使用率（%） */
  cpu_percent: number;
  /** 内存使用率（%） */
  memory_percent: number;
  /** 已用内存（MB） */
  memory_used_mb: number;
  /** 磁盘使用率（%） */
  disk_percent: number;
  /** 已用磁盘（MB） */
  disk_used_mb: number;
  /** 磁盘总量（MB） */
  disk_total_mb: number;
  /** 网络发送字节数 */
  net_bytes_sent: number;
  /** 网络接收字节数 */
  net_bytes_recv: number;
  /** 网络发送速率（KB/s） */
  net_send_rate_kb: number;
  /** 网络接收速率（KB/s） */
  net_recv_rate_kb: number;
  /** 丢包率 */
  net_packet_loss_rate: number;
  /** 1 分钟负载 */
  cpu_load_1: number;
  /** 5 分钟负载 */
  cpu_load_5: number;
  /** 15 分钟负载 */
  cpu_load_15: number;
  /** 记录时间 */
  recorded_at: string;
  timestamp?: string;
  /** 允许额外的动态字段 */
  [key: string]: unknown;
}

/** 主机列表分页响应 */
export interface HostListResponse {
  items: Host[];
  total: number;
  page: number;
  page_size: number;
}

/** 主机服务 */
export const hostService = {
  /** 获取主机列表（支持分页和筛选） */
  list: (params?: Record<string, unknown>) => api.get<HostListResponse>('/hosts', { params }),
  /** 获取单台主机详情 */
  get: (id: string) => api.get<Host>(`/hosts/${id}`),
  /** 获取主机性能指标历史 */
  getMetrics: (id: string, params?: Record<string, unknown>) =>
    api.get<HostMetrics[]>(`/hosts/${id}/metrics`, { params }),
};
