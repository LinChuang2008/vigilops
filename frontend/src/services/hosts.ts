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
  memory_total: number;
  memory_used: number;
  disk_percent: number;
  disk_total: number;
  disk_used: number;
  net_bytes_sent: number;
  net_bytes_recv: number;
  load_avg_1: number;
  load_avg_5: number;
  load_avg_15: number;
  timestamp: string;
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
