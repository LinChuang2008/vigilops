// Phase 2: logs + databases + enhanced alerts
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
import Logs from './pages/Logs';
import Databases from './pages/Databases';
import DatabaseDetail from './pages/DatabaseDetail';

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
            <Route path="/login" element={<Login />} />
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
              <Route path="/settings" element={<Settings />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
