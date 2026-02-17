/**
 * 路由鉴权守卫组件
 *
 * 包裹需要登录才能访问的页面，检查 localStorage 中是否存在 access_token。
 * 未登录时自动重定向到登录页，并记录来源路径以便登录后跳回。
 */
import { Navigate, useLocation } from 'react-router-dom';

/**
 * 鉴权守卫组件
 *
 * @param children - 需要保护的子组件
 * @returns 已认证时渲染子组件，未认证时重定向至登录页
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  const location = useLocation();

  if (!token) {
    // 未登录，重定向到登录页并携带当前路径信息
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
