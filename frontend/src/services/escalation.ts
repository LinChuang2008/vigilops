/**
 * 告警升级 API 服务
 */
import api from './api';

export const escalationService = {
  // 升级规则
  listRules: (params?: Record<string, unknown>) => api.get('/alert-escalation/rules', { params }),
  getRule: (id: number) => api.get(`/alert-escalation/rules/${id}`),
  createRule: (data: Record<string, unknown>) => api.post('/alert-escalation/rules', data),
  updateRule: (id: number, data: Record<string, unknown>) => api.put(`/alert-escalation/rules/${id}`, data),
  deleteRule: (id: number) => api.delete(`/alert-escalation/rules/${id}`),

  // 手动升级
  manualEscalate: (alertId: number, data: { to_severity: string; message?: string }) =>
    api.post(`/alert-escalation/alerts/${alertId}/escalate`, data),

  // 升级历史
  listHistory: (params?: Record<string, unknown>) => api.get('/alert-escalation/history', { params }),
  getAlertEscalations: (alertId: number) => api.get(`/alert-escalation/alerts/${alertId}/escalations`),

  // 统计
  getStats: (params?: Record<string, unknown>) => api.get('/alert-escalation/stats', { params }),

  // 引擎扫描
  triggerScan: () => api.post('/alert-escalation/engine/scan'),
};
