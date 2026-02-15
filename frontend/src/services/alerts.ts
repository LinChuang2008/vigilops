import api from './api';

export interface Alert {
  id: string;
  host_id: string | null;
  service_id: string | null;
  rule_id: string;
  severity: string;
  status: string;
  title: string;
  message: string;
  fired_at: string;
  resolved_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
}

export interface AlertRule {
  id: string;
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  duration_seconds: number;
  severity: string;
  enabled: boolean;
  is_builtin: boolean;
  is_enabled: boolean;
  created_at: string;
  rule_type?: string;
  log_keyword?: string;
  log_level?: string;
  log_service?: string;
  db_metric_name?: string;
  db_id?: number;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
}

export const alertService = {
  list: (params?: Record<string, unknown>) => api.get<AlertListResponse>('/alerts', { params }),
  get: (id: string) => api.get<Alert>(`/alerts/${id}`),
  ack: (id: string) => api.post(`/alerts/${id}/ack`),
  listRules: (params?: Record<string, unknown>) => api.get<AlertRule[]>('/alert-rules', { params }),
  createRule: (data: Partial<AlertRule>) => api.post('/alert-rules', data),
  updateRule: (id: string, data: Partial<AlertRule>) => api.put(`/alert-rules/${id}`, data),
  deleteRule: (id: string) => api.delete(`/alert-rules/${id}`),
};
