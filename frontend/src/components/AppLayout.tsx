/**
 * 应用主布局组件
 *
 * 提供侧边栏导航、顶部栏（含用户菜单）和内容区域的整体页面框架。
 * 所有需要认证的页面均嵌套在此布局内，通过 React Router 的 <Outlet /> 渲染子路由。
 * 支持移动端响应式设计，在小屏幕上使用抽屉式侧边栏。
 */
import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, theme, Avatar, Dropdown, Drawer } from 'antd';
import { useTranslation } from 'react-i18next';
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
  GlobalOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

/** viewer 可见的菜单 key */
const viewerKeys = new Set(['/', '/hosts', '/services', 'topology-group', '/topology', '/topology/servers', '/topology/service-groups', '/logs', '/databases', '/alerts', '/ai-analysis']);
/** member 隐藏的菜单 key */
const memberHiddenKeys = new Set(['/users', '/settings']);

/** 根据角色过滤菜单 */
function filterMenuByRole(items: ReturnType<typeof buildMenuItems>, role: string) {
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

/** 生成侧边栏菜单项，使用 i18n 翻译 */
function buildMenuItems(t: (key: string) => string) {
  return [
    { key: '/', icon: <DashboardOutlined />, label: t('menu.dashboard') },
    { key: '/hosts', icon: <CloudServerOutlined />, label: t('menu.hosts') },
    { key: '/services', icon: <ApiOutlined />, label: t('menu.services') },
    { key: 'topology-group', icon: <DeploymentUnitOutlined />, label: t('menu.topology'),
      children: [
        { key: '/topology', label: t('menu.topologyService') },
        { key: '/topology/servers', label: t('menu.topologyServers') },
        { key: '/topology/service-groups', label: t('menu.topologyServiceGroups') },
      ],
    },
    { key: '/logs', icon: <FileTextOutlined />, label: t('menu.logs') },
    { key: '/databases', icon: <DatabaseOutlined />, label: t('menu.databases') },
    { key: '/alerts', icon: <AlertOutlined />, label: t('menu.alerts') },
    { key: '/alert-escalation', icon: <RiseOutlined />, label: t('menu.alertEscalation') },
    { key: '/on-call', icon: <ScheduleOutlined />, label: t('menu.onCall') },
    { key: '/remediations', icon: <ThunderboltOutlined />, label: t('menu.remediation') },
    { key: '/sla', icon: <SafetyCertificateOutlined />, label: t('menu.sla') },
    { key: '/ai-analysis', icon: <RobotOutlined />, label: t('menu.aiAnalysis') },
    { key: '/reports', icon: <FileSearchOutlined />, label: t('menu.reports') },
    { key: '/notification-channels', icon: <NotificationOutlined />, label: t('menu.notificationChannels') },
    { key: '/notification-templates', icon: <FormOutlined />, label: t('menu.notificationTemplates') },
    { key: '/notification-logs', icon: <UnorderedListOutlined />, label: t('menu.notificationLogs') },
    { key: '/users', icon: <TeamOutlined />, label: t('menu.users') },
    { key: '/audit-logs', icon: <AuditOutlined />, label: t('menu.auditLogs') },
    { key: '/settings', icon: <SettingOutlined />, label: t('menu.settings') },
  ];
}

/**
 * 应用主布局组件
 *
 * 包含可折叠侧边栏、顶部导航栏（用户头像与退出登录）、以及子路由内容区域。
 * 在移动端使用抽屉式侧边栏以优化用户体验。
 */
export default function AppLayout() {
  /** 侧边栏折叠状态 */
  const [collapsed, setCollapsed] = useState(false);
  /** 移动端抽屉打开状态 */
  const [drawerVisible, setDrawerVisible] = useState(false);
  /** 是否为移动端 */
  const [isMobile, setIsMobile] = useState(false);
  
  const navigate = useNavigate();
  const location = useLocation();
  const { token: { colorBgContainer, borderRadiusLG, colorBgLayout } } = theme.useToken();
  const { isDark, toggleTheme } = useTheme();
  const { t, i18n } = useTranslation();

  /** 动态生成菜单 */
  const allMenuItems = buildMenuItems(t);

  /** 切换语言 */
  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
  };

  /** 检测屏幕大小变化 */
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setCollapsed(true); // 移动端默认折叠侧边栏
      }
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

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

  /** 处理菜单点击 - 移动端自动关闭抽屉 */
  const handleMenuClick = ({ key }: { key: string }) => {
    if (!key.includes('-group')) {
      navigate(key);
      if (isMobile) {
        setDrawerVisible(false); // 移动端点击菜单后关闭抽屉
      }
    }
  };

  /** 切换侧边栏/抽屉 */
  const toggleSidebar = () => {
    if (isMobile) {
      setDrawerVisible(!drawerVisible);
    } else {
      setCollapsed(!collapsed);
    }
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

  /** 渲染菜单内容 */
  const renderMenuContent = (inDrawer = false) => (
    <>
      {/* 品牌标识区域 */}
      <div style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: inDrawer ? 'inherit' : '#fff',
        fontSize: (inDrawer || !collapsed) ? 20 : 16,
        fontWeight: 'bold',
        letterSpacing: 2,
        borderBottom: inDrawer ? '1px solid #f0f0f0' : undefined,
      }}>
        {(inDrawer || !collapsed) ? 'VigilOps' : 'VO'}
      </div>
      <Menu
        theme={inDrawer ? 'light' : 'dark'}
        mode="inline"
        selectedKeys={[selectedKey]}
        defaultOpenKeys={openKey ? [openKey] : []}
        items={menuItems}
        onClick={handleMenuClick}
      />
    </>
  );

  return (
    <Layout style={{ minHeight: '100vh', background: colorBgLayout }}>
      {/* 桌面端侧边栏 */}
      {!isMobile && (
        <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
          {renderMenuContent()}
        </Sider>
      )}

      {/* 移动端抽屉 */}
      {isMobile && (
        <Drawer
          title={null}
          placement="left"
          closable={false}
          onClose={() => setDrawerVisible(false)}
          open={drawerVisible}
          bodyStyle={{ padding: 0 }}
          width={280}
        >
          {renderMenuContent(true)}
        </Drawer>
      )}
      <Layout>
        <Header style={{
          padding: isMobile ? '0 16px' : '0 24px',
          background: colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          {/* 侧边栏折叠切换按钮 */}
          <Button
            type="text"
            icon={isMobile ? <MenuUnfoldOutlined /> : (collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />)}
            onClick={toggleSidebar}
            size={isMobile ? 'large' : 'middle'}
          />
          {/* 右侧操作区：主题切换 + 用户菜单 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Dropdown menu={{
              items: [
                { key: 'zh', label: '🇨🇳 中文', onClick: () => changeLanguage('zh') },
                { key: 'en', label: '🇺🇸 English', onClick: () => changeLanguage('en') },
              ],
              selectedKeys: [i18n.language],
            }}>
              <Button type="text" icon={<GlobalOutlined />} title={t('header.language')}>
                {i18n.language === 'zh' ? '中文' : 'EN'}
              </Button>
            </Dropdown>
            <Button
              type="text"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              title={isDark ? t('header.lightMode') : t('header.darkMode')}
            />
            <Dropdown menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: t('header.logout'), onClick: handleLogout },
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
          margin: isMobile ? 12 : 24,
          padding: isMobile ? 16 : 24,
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
