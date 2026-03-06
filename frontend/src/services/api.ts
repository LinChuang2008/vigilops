/**
 * Axios 实例配置模块
 * 创建全局 API 请求实例，统一处理请求鉴权和响应错误
 */
import axios from 'axios';

/** 创建 Axios 实例，统一配置基础路径、超时和请求头 */
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

/**
 * AI 专用 Axios 实例：超时设为 60s
 * AI 分析/Chat 接口响应时间较长（20-30s），需要单独配置
 */
export const aiApi = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

/** 请求拦截器：自动附加 JWT 令牌到请求头 */
const attachToken = (config: any) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

api.interceptors.request.use(attachToken);
aiApi.interceptors.request.use(attachToken);

/**
 * 响应拦截器：统一处理 401 未授权错误
 * 清除本地存储的令牌并跳转到登录页
 */
const handleAuthError = (error: any) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
  return Promise.reject(error);
};

api.interceptors.response.use((response) => response, handleAuthError);
aiApi.interceptors.response.use((response) => response, handleAuthError);

export default api;
