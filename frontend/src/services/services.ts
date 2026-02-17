/**
 * 服务监控模块
 * 提供服务列表、详情和健康检查记录的 API 调用
 */
import api from './api';

/** 被监控的服务 */
export interface Service {
  id: string;
  /** 服务名称 */
  name: string;
  /** 服务访问地址 */
  url?: string;
  /** 检测目标（IP 或域名） */
  target?: string;
  /** 服务类型 */
  type?: string;
  /** 检测方式（http / tcp / ping 等） */
  check_type?: string;
  /** 当前状态（healthy / unhealthy / unknown） */
  status: string;
  /** 可用率（%） */
  uptime_percent: number;
  /** 最后检测时间 */
  last_check?: string | null;
  /** 是否启用监控 */
  is_active?: boolean;
  /** 关联主机 ID */
  host_id?: number;
  created_at: string;
}

/** 服务健康检查记录 */
export interface ServiceCheck {
  id: string;
  service_id: string;
  /** 检查结果状态 */
  status: string;
  /** 响应时间（毫秒） */
  response_time_ms: number;
  /** HTTP 状态码 */
  status_code: number | null;
  /** 错误信息 */
  error: string | null;
  /** 检查时间 */
  checked_at: string;
}

/** 服务列表分页响应 */
export interface ServiceListResponse {
  items: Service[];
  total: number;
  page: number;
  page_size: number;
}

/** 服务监控服务 */
export const serviceService = {
  /** 获取服务列表（支持分页和筛选） */
  list: (params?: Record<string, unknown>) => api.get<ServiceListResponse>('/services', { params }),
  /** 获取单个服务详情 */
  get: (id: string) => api.get<Service>(`/services/${id}`),
  /** 获取服务健康检查历史记录 */
  getChecks: (id: string, params?: Record<string, unknown>) =>
    api.get<ServiceCheck[]>(`/services/${id}/checks`, { params }),
};
