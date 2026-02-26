/**
 * 应用主布局组件
 *
 * 提供侧边栏导航、顶部栏（含用户菜单）和内容区域的整体页面框架。
 * 所有需要认证的页面均嵌套在此布局内，通过 React Router 的 <Outlet /> 渲染子路由。
 */
import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, theme, Avatar, Dropdown } from 'antd';
import { useTheme } from '../contexts/ThemeContext';
import {
  DashboardOutlined,
  SunOutlined,
  MoonOutlined,
  CloudServerOutlined,
  ApiOutlined,
  AlertOutlined,
  FileTextOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  DatabaseOutlined,
  NotificationOutlined,
  UnorderedListOutlined,
  FormOutlined,
  RobotOutlined,
  TeamOutlined,
  AuditOutlined,
  FileSearchOutlined,
  DeploymentUnitOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  ScheduleOutlined,
  RiseOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

/** viewer 可见的菜单 key */
const viewerKeys = new Set(['/', '/hosts', '/services', 'topology-group', '/topology', '/topology/servers', '/topology/service-groups', '/logs', '/databases', '/alerts', '/ai-analysis']);
/** member 隐藏的菜单 key */
const memberHiddenKeys = new Set(['/users', '/settings']);

/** 根据角色过滤菜单 */
function filterMenuByRole(items: typeof allMenuItems, role: string) {
  if (role === 'admin') return items;
  return items
    .filter((item) => {
      if (role === 'viewer') return viewerKeys.has(item.key);
      if (role === 'member') return !memberHiddenKeys.has(item.key);
      return true;
    })
    .map((item) => {
      if ('children' in item && Array.isArray((item as any).children) && role === 'viewer') {
        return { ...item, children: (item as any).children.filter((c: any) => viewerKeys.has(c.key)) };
      }
      return item;
    });
}

/** 侧边栏菜单项配置，key 对应路由路径 */
const allMenuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/hosts', icon: <CloudServerOutlined />, label: '服务器' },
  { key: '/services', icon: <ApiOutlined />, label: '服务监控' },
  { key: 'topology-group', icon: <DeploymentUnitOutlined />, label: '拓扑图',
    children: [
      { key: '/topology', label: '服务拓扑' },
      { key: '/topology/servers', label: '多服务器' },
      { key: '/topology/service-groups', label: '服务组' },
    ],
  },
  { key: '/logs', icon: <FileTextOutlined />, label: '日志管理' },
  { key: '/databases', icon: <DatabaseOutlined />, label: '数据库监控' },
  { key: '/alerts', icon: <AlertOutlined />, label: '告警中心' },
  { key: '/alert-escalation', icon: <RiseOutlined />, label: '告警升级' },
  { key: '/on-call', icon: <ScheduleOutlined />, label: '值班排期' },
  { key: '/remediations', icon: <ThunderboltOutlined />, label: '自动修复' },
  { key: '/sla', icon: <SafetyCertificateOutlined />, label: 'SLA 管理' },
  { key: '/ai-analysis', icon: <RobotOutlined />, label: 'AI 分析' },
  { key: '/reports', icon: <FileSearchOutlined />, label: '运维报告' },
  { key: '/notification-channels', icon: <NotificationOutlined />, label: '通知渠道' },
  { key: '/notification-templates', icon: <FormOutlined />, label: '通知模板' },
  { key: '/notification-logs', icon: <UnorderedListOutlined />, label: '通知日志' },
  { key: '/users', icon: <TeamOutlined />, label: '用户管理' },
  { key: '/audit-logs', icon: <AuditOutlined />, label: '审计日志' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

/**
 * 应用主布局组件
 *
 * 包含可折叠侧边栏、顶部导航栏（用户头像与退出登录）、以及子路由内容区域。
 */
export default function AppLayout() {
  /** 侧边栏折叠状态 */
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token: { colorBgContainer, borderRadiusLG, colorBgLayout } } = theme.useToken();
  const { isDark, toggleTheme } = useTheme();

  /** 从 localStorage 读取用户名和角色 */
  const userName = localStorage.getItem('user_name') || 'Admin';
  const userRole = localStorage.getItem('user_role') || 'viewer';
  const menuItems = filterMenuByRole(allMenuItems, userRole);

  /** 退出登录：清除本地存储的认证信息并跳转到登录页 */
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_role');
    navigate('/login');
  };

  /** 根据当前路径匹配侧边栏选中菜单项（支持嵌套子菜单） */
  const findSelectedKey = (): string => {
    const path = location.pathname;
    // 先在子菜单里找精确匹配
    for (const item of allMenuItems) {
      if ('children' in item && Array.isArray((item as any).children)) {
        for (const child of (item as any).children) {
          if (child.key !== '/' && path.startsWith(child.key)) return child.key;
        }
      }
    }
    // 再在顶层找
    const found = allMenuItems.find(
      (item) => item.key !== '/' && !item.key.includes('-group') && path.startsWith(item.key)
    );
    return found?.key || '/';
  };
  const selectedKey = findSelectedKey();
  const openKey = allMenuItems.find(
    (item) => 'children' in item && (item as any).children?.some((c: any) => c.key === selectedKey)
  )?.key;

  return (
    <Layout style={{ minHeight: '100vh', background: colorBgLayout }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
        {/* 品牌标识区域，折叠时显示缩写 */}
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: collapsed ? 16 : 20,
          fontWeight: 'bold',
          letterSpacing: 2,
        }}>
          {collapsed ? 'VO' : 'VigilOps'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={openKey ? [openKey] : []}
          items={menuItems}
          onClick={({ key }) => { if (!key.includes('-group')) navigate(key); }}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          {/* 侧边栏折叠切换按钮 */}
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          {/* 右侧操作区：主题切换 + 用户菜单 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button
              type="text"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              title={isDark ? '切换亮色模式' : '切换暗色模式'}
            />
            <Dropdown menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
              ],
            }}>
              <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar icon={<UserOutlined />} size="small" />
                <span>{userName}</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content style={{
          margin: 24,
          padding: 24,
          background: colorBgContainer,
          borderRadius: borderRadiusLG,
          minHeight: 280,
        }}>
          {/* 子路由内容渲染区 */}
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
