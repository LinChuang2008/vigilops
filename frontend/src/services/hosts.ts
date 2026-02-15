import api from './api';

export interface Host {
  id: string;
  hostname: string;
  ip_address: string;
  os: string;
  status: string;
  tags: Record<string, boolean> | string[] | null;
  group: string;
  last_heartbeat: string | null;
  created_at: string;
  latest_metrics?: HostMetrics;
}

export interface HostMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  disk_percent: number;
  disk_used_mb: number;
  disk_total_mb: number;
  net_bytes_sent: number;
  net_bytes_recv: number;
  net_send_rate_kb: number;
  net_recv_rate_kb: number;
  net_packet_loss_rate: number;
  cpu_load_1: number;
  cpu_load_5: number;
  cpu_load_15: number;
  recorded_at: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface HostListResponse {
  items: Host[];
  total: number;
  page: number;
  page_size: number;
}

export const hostService = {
  list: (params?: Record<string, unknown>) => api.get<HostListResponse>('/hosts', { params }),
  get: (id: string) => api.get<Host>(`/hosts/${id}`),
  getMetrics: (id: string, params?: Record<string, unknown>) =>
    api.get<HostMetrics[]>(`/hosts/${id}/metrics`, { params }),
};
