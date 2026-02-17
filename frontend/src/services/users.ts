/**
 * 用户管理与审计日志 API 服务
 * 提供用户 CRUD、密码重置和审计日志查询接口
 */
import api from './api';

/** 用户信息 */
export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** 创建用户请求参数 */
export interface UserCreate {
  email: string;
  name: string;
  password: string;
  role: string;
}

/** 更新用户请求参数 */
export interface UserUpdate {
  name?: string;
  role?: string;
  is_active?: boolean;
}

/** 审计日志条目 */
export interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  resource_type: string;
  resource_id: number | null;
  detail: string | null;
  ip_address: string | null;
  created_at: string;
  user_name?: string;
}

/** 审计日志查询参数 */
export interface AuditLogParams {
  page?: number;
  page_size?: number;
  action?: string;
  user_id?: number;
}

/** 获取用户列表 */
export function fetchUsers(page = 1, pageSize = 20) {
  return api.get<{ items: User[]; total: number }>('/users', {
    params: { page, page_size: pageSize },
  });
}

/** 创建用户 */
export function createUser(data: UserCreate) {
  return api.post<User>('/users', data);
}

/** 更新用户信息 */
export function updateUser(id: number, data: UserUpdate) {
  return api.put<User>(`/users/${id}`, data);
}

/** 删除用户 */
export function deleteUser(id: number) {
  return api.delete(`/users/${id}`);
}

/** 重置用户密码 */
export function resetPassword(id: number, newPassword: string) {
  return api.put(`/users/${id}/password`, { password: newPassword });
}

/** 获取审计日志列表 */
export function fetchAuditLogs(params: AuditLogParams = {}) {
  return api.get<{ items: AuditLog[]; total: number }>('/audit-logs', { params });
}
