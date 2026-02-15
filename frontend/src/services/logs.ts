import api from './api';

export interface LogEntry {
  id: string;
  timestamp: string;
  host_id: string;
  hostname: string;
  service: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
  message: string;
  file_path?: string;
  source?: string;
}

export interface LogsResponse {
  items: LogEntry[];
  total: number;
}

export interface LogStats {
  period: string;
  total: number;
  by_level: Record<string, number>;
}

export interface LogQueryParams {
  keyword?: string;
  host_id?: string;
  service?: string;
  level?: string[];
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export async function fetchLogs(params: LogQueryParams): Promise<LogsResponse> {
  const query: Record<string, unknown> = { ...params };
  if (params.level && params.level.length > 0) {
    query.level = params.level.join(',');
  }
  const res = await api.get('/logs', { params: query });
  return res.data;
}

export async function fetchLogStats(period: string = '1h'): Promise<LogStats> {
  const res = await api.get('/logs/stats', { params: { period } });
  return res.data;
}
