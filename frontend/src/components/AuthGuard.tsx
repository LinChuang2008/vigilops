/**
 * 路由鉴权守卫组件
 *
 * JWT 已迁移至 httpOnly Cookie，无法从 JS 直接读取 token。
 * 通过 localStorage 中的 user_name 作为会话指示符（非敏感信息）判断是否登录。
 * 如果 cookie 已过期但 user_name 仍在，后续 API 调用会收到 401 并通过
 * api.ts 的响应拦截器清除 user_name 并跳转登录页。
 */
import { Navigate, useLocation } from 'react-router-dom';

/**
 * 鉴权守卫组件
 *
 * @param children - 需要保护的子组件
 * @returns 已认证时渲染子组件，未认证时重定向至登录页
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  // 用 user_name 作为会话指示符（httpOnly cookie 不可被 JS 直接读取）
  const isLoggedIn = !!localStorage.getItem('user_name');
  const location = useLocation();

  if (!isLoggedIn) {
    // 未登录，重定向到登录页并携带当前路径信息
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
