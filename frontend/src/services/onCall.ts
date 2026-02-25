/**
 * 值班排期 API 服务
 */
import api from './api';

export const onCallService = {
  // 值班组
  listGroups: (params?: Record<string, unknown>) => api.get('/on-call/groups', { params }),
  getGroup: (id: number) => api.get(`/on-call/groups/${id}`),
  createGroup: (data: Record<string, unknown>) => api.post('/on-call/groups', data),
  updateGroup: (id: number, data: Record<string, unknown>) => api.put(`/on-call/groups/${id}`, data),
  deleteGroup: (id: number) => api.delete(`/on-call/groups/${id}`),

  // 排期
  listSchedules: (params?: Record<string, unknown>) => api.get('/on-call/schedules', { params }),
  getSchedule: (id: number) => api.get(`/on-call/schedules/${id}`),
  createSchedule: (data: Record<string, unknown>) => api.post('/on-call/schedules', data),
  updateSchedule: (id: number, data: Record<string, unknown>) => api.put(`/on-call/schedules/${id}`, data),
  deleteSchedule: (id: number) => api.delete(`/on-call/schedules/${id}`),

  // 当前值班
  getCurrentOnCall: (groupId?: number) => api.get('/on-call/current', { params: groupId ? { group_id: groupId } : {} }),

  // 覆盖情况
  getCoverage: (startDate: string, endDate: string) =>
    api.get('/on-call/coverage', { params: { start_date: startDate, end_date: endDate } }),
};
