/**
 * 应用根组件
 * 配置 Ant Design 主题与国际化，定义全局路由结构
 * 所有需要认证的页面由 AuthGuard 守卫保护，嵌套在 AppLayout 布局内
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/AppLayout';
import AuthGuard from './components/AuthGuard';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import HostList from './pages/HostList';
import HostDetail from './pages/HostDetail';
import ServiceList from './pages/ServiceList';
import ServiceDetail from './pages/ServiceDetail';
import AlertList from './pages/AlertList';
import Settings from './pages/Settings';
import NotificationChannels from './pages/NotificationChannels';
import NotificationLogs from './pages/NotificationLogs';
import NotificationTemplates from './pages/NotificationTemplates';
import Logs from './pages/Logs';
import Databases from './pages/Databases';
import DatabaseDetail from './pages/DatabaseDetail';
import AIAnalysis from './pages/AIAnalysis';
import Users from './pages/Users';
import AuditLogs from './pages/AuditLogs';
import Reports from './pages/Reports';

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <Routes>
            {/* 登录页（无需认证） */}
            <Route path="/login" element={<Login />} />
            {/* 需要认证的路由，统一使用 AppLayout 布局 */}
            <Route
              element={
                <AuthGuard>
                  <AppLayout />
                </AuthGuard>
              }
            >
              <Route path="/" element={<Dashboard />} />
              <Route path="/hosts" element={<HostList />} />
              <Route path="/hosts/:id" element={<HostDetail />} />
              <Route path="/services" element={<ServiceList />} />
              <Route path="/services/:id" element={<ServiceDetail />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/databases" element={<Databases />} />
              <Route path="/databases/:id" element={<DatabaseDetail />} />
              <Route path="/alerts" element={<AlertList />} />
              <Route path="/ai-analysis" element={<AIAnalysis />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/notification-channels" element={<NotificationChannels />} />
              <Route path="/notification-templates" element={<NotificationTemplates />} />
              <Route path="/notification-logs" element={<NotificationLogs />} />
              <Route path="/users" element={<Users />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
            {/* 未匹配路由重定向到首页 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
