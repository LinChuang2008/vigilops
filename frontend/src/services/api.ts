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
});

/** 请求拦截器：自动附加 JWT 令牌到请求头 */
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * 响应拦截器：统一处理 401 未授权错误
 * 清除本地存储的令牌并跳转到登录页
 */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // 避免在登录页重复跳转
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
