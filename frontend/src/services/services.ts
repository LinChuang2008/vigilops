import api from './api';

export interface Service {
  id: string;
  name: string;
  url?: string;
  target?: string;
  type?: string;
  check_type?: string;
  status: string;
  uptime_percent: number;
  last_check?: string | null;
  is_active?: boolean;
  host_id?: number;
  created_at: string;
}

export interface ServiceCheck {
  id: string;
  service_id: string;
  status: string;
  response_time_ms: number;
  status_code: number | null;
  error: string | null;
  checked_at: string;
}

export interface ServiceListResponse {
  items: Service[];
  total: number;
  page: number;
  page_size: number;
}

export const serviceService = {
  list: (params?: Record<string, unknown>) => api.get<ServiceListResponse>('/services', { params }),
  get: (id: string) => api.get<Service>(`/services/${id}`),
  getChecks: (id: string, params?: Record<string, unknown>) =>
    api.get<ServiceCheck[]>(`/services/${id}/checks`, { params }),
};
