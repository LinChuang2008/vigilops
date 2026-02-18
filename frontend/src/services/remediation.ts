/**
 * 自动修复服务模块
 * 提供修复任务的 API 调用方法
 */
import api from './api';

/** 修复任务 */
export interface Remediation {
  id: string;
  alert_id: string;
  alert_name: string;
  host: string;
  status: 'pending' | 'approved' | 'executing' | 'success' | 'failed' | 'rejected';
  runbook: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  diagnosis: string;
  commands: RemediationCommand[];
  created_at: string;
  updated_at: string;
  approved_by?: string;
  approved_at?: string;
}

/** 修复命令执行记录 */
export interface RemediationCommand {
  command: string;
  output: string;
  exit_code: number;
  executed_at: string;
}

/** 修复列表分页响应 */
export interface RemediationListResponse {
  items: Remediation[];
  total: number;
  page: number;
  page_size: number;
}

/** 修复任务服务 */
export const remediationService = {
  /** 获取修复列表（支持分页和筛选） */
  list: (params?: Record<string, unknown>) =>
    api.get<RemediationListResponse>('/remediations', { params }),

  /** 获取单条修复详情 */
  get: (id: string) => api.get<Remediation>(`/remediations/${id}`),

  /** 审批通过 */
  approve: (id: string) => api.post(`/remediations/${id}/approve`),

  /** 审批拒绝 */
  reject: (id: string) => api.post(`/remediations/${id}/reject`),

  /** 重新执行 */
  retry: (id: string) => api.post(`/remediations/${id}/retry`),
};
