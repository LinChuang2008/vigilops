/**
 * 认证服务模块
 * 提供用户登录、注册、令牌刷新及获取当前用户信息的 API 调用
 */
import api from './api';

/** 登录请求参数 */
export interface LoginRequest {
  email: string;
  password: string;
}

/** 注册请求参数 */
export interface RegisterRequest {
  email: string;
  name: string;
  password: string;
}

/** 认证响应（登录/注册/刷新令牌共用） */
export interface AuthResponse {
  /** 访问令牌 */
  access_token: string;
  /** 刷新令牌 */
  refresh_token: string;
  /** 令牌类型（Bearer） */
  token_type: string;
}

/** 用户信息 */
export interface User {
  id: string;
  email: string;
  name: string;
  /** 用户角色（admin / viewer 等） */
  role: string;
  /** 是否激活 */
  is_active: boolean;
  created_at: string;
}

/** 认证服务 */
export const authService = {
  /** 用户登录 */
  login: (data: LoginRequest) => api.post<AuthResponse>('/auth/login', data),
  /** 用户注册 */
  register: (data: RegisterRequest) => api.post<AuthResponse>('/auth/register', data),
  /** 获取当前登录用户信息 */
  me: () => api.get<User>('/auth/me'),
  /** 使用刷新令牌获取新的访问令牌 */
  refresh: (refresh_token: string) => api.post<AuthResponse>('/auth/refresh', { refresh_token }),
};
