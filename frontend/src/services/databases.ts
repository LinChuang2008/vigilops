import api from './api';

export interface DatabaseItem {
  id: number;
  host_id: number;
  name: string;
  db_type: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  latest_metrics?: {
    connections_total: number | null;
    connections_active: number | null;
    database_size_mb: number | null;
    slow_queries: number | null;
    tables_count: number | null;
    transactions_committed: number | null;
    transactions_rolled_back: number | null;
    qps: number | null;
    tablespace_used_pct: number | null;
    recorded_at: string | null;
  };
}

export interface SlowQuery {
  sql_id: string;
  avg_seconds: number;
  executions: number;
  sql_text: string;
}

export interface SlowQueriesResponse {
  database_id: number;
  slow_queries: SlowQuery[];
}

export interface DatabaseMetric {
  connections_total: number | null;
  connections_active: number | null;
  database_size_mb: number | null;
  slow_queries: number | null;
  tables_count: number | null;
  transactions_committed: number | null;
  transactions_rolled_back: number | null;
  qps: number | null;
  tablespace_used_pct: number | null;
  recorded_at: string | null;
}

export interface DatabaseListResponse {
  databases: DatabaseItem[];
  total: number;
}

export interface DatabaseMetricsResponse {
  database_id: number;
  period: string;
  metrics: DatabaseMetric[];
}

export const databaseService = {
  list: (params?: Record<string, unknown>) => api.get<DatabaseListResponse>('/databases', { params }),
  get: (id: number | string) => api.get<DatabaseItem>(`/databases/${id}`),
  getMetrics: (id: number | string, period = '1h') => api.get<DatabaseMetricsResponse>(`/databases/${id}/metrics`, { params: { period } }),
  getSlowQueries: (id: number | string) => api.get<SlowQueriesResponse>(`/databases/${id}/slow-queries`),
};
