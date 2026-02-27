/**
 * 通用状态组件 - 空状态、错误状态、加载状态
 * 
 * 提供统一的空数据、错误提示和加载中体验，
 * 各页面复用这些组件以保持设计一致性。
 */
import { Empty, Result, Button, Space, Typography, Spin } from 'antd';
import {
  ReloadOutlined,
  WifiOutlined,
  LockOutlined,
  CloudServerOutlined,
  AlertOutlined,
  BellOutlined,
  FileTextOutlined,
  ApartmentOutlined,
  DashboardOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';

const { Text } = Typography;

/* ==================== 错误类型判断 ==================== */

export type ErrorType = 'network' | 'permission' | 'server' | 'notfound' | 'unknown';

/** 根据错误对象推断错误类型 */
export function classifyError(error: unknown): ErrorType {
  if (!error) return 'unknown';
  const err = error as { response?: { status?: number }; message?: string; code?: string };
  if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) return 'network';
  const status = err.response?.status;
  if (status === 401 || status === 403) return 'permission';
  if (status === 404) return 'notfound';
  if (status && status >= 500) return 'server';
  return 'unknown';
}

/* ==================== 错误状态配置 ==================== */

function getErrorConfig(t: TFunction): Record<ErrorType, { icon: React.ReactNode; title: string; description: string }> {
  return {
    network: {
      icon: <WifiOutlined style={{ fontSize: 48, color: '#faad14' }} />,
      title: t('state.error.network.title'),
      description: t('state.error.network.description'),
    },
    permission: {
      icon: <LockOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />,
      title: t('state.error.permission.title'),
      description: t('state.error.permission.description'),
    },
    server: {
      icon: <CloudServerOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />,
      title: t('state.error.server.title'),
      description: t('state.error.server.description'),
    },
    notfound: {
      icon: <CloudServerOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />,
      title: t('state.error.notfound.title'),
      description: t('state.error.notfound.description'),
    },
    unknown: {
      icon: <CloudServerOutlined style={{ fontSize: 48, color: '#faad14' }} />,
      title: t('state.error.unknown.title'),
      description: t('state.error.unknown.description'),
    },
  };
}

/* ==================== ErrorState 组件 ==================== */

interface ErrorStateProps {
  /** 错误类型，不传则自动推断 */
  type?: ErrorType;
  /** 原始错误对象，用于自动推断类型 */
  error?: unknown;
  /** 自定义标题 */
  title?: string;
  /** 自定义描述 */
  description?: string;
  /** 重试回调 */
  onRetry?: () => void;
  /** 是否全屏居中 */
  fullScreen?: boolean;
}

/**
 * 统一错误状态组件
 * 根据错误类型显示对应的图标、标题和描述，提供重试按钮
 */
export function ErrorState({ type, error, title, description, onRetry, fullScreen }: ErrorStateProps) {
  const { t } = useTranslation();
  const errorType = type || classifyError(error);
  const config = getErrorConfig(t)[errorType];

  const content = (
    <Result
      icon={config.icon}
      title={title || config.title}
      subTitle={description || config.description}
      extra={
        onRetry ? (
          <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
            {t('state.error.retry')}
          </Button>
        ) : undefined
      }
    />
  );

  if (fullScreen) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
        {content}
      </div>
    );
  }

  return content;
}

/* ==================== 空状态配置 ==================== */

type EmptyScene = 'dashboard' | 'servers' | 'alerts' | 'notifications' | 'reports' | 'topology' | 'default';

function getEmptyConfig(t: TFunction): Record<EmptyScene, { icon: React.ReactNode; title: string; description: string; actionText?: string }> {
  return {
    dashboard: {
      icon: <DashboardOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
      title: t('state.empty.dashboard.title'),
      description: t('state.empty.dashboard.description'),
      actionText: t('state.empty.dashboard.actionText'),
    },
    servers: {
      icon: <CloudServerOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
      title: t('state.empty.servers.title'),
      description: t('state.empty.servers.description'),
      actionText: t('state.empty.servers.actionText'),
    },
    alerts: {
      icon: <AlertOutlined style={{ fontSize: 48, color: '#52c41a' }} />,
      title: t('state.empty.alerts.title'),
      description: t('state.empty.alerts.description'),
      actionText: t('state.empty.alerts.actionText'),
    },
    notifications: {
      icon: <BellOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
      title: t('state.empty.notifications.title'),
      description: t('state.empty.notifications.description'),
      actionText: t('state.empty.notifications.actionText'),
    },
    reports: {
      icon: <FileTextOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
      title: t('state.empty.reports.title'),
      description: t('state.empty.reports.description'),
      actionText: t('state.empty.reports.actionText'),
    },
    topology: {
      icon: <ApartmentOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
      title: t('state.empty.topology.title'),
      description: t('state.empty.topology.description'),
    },
    default: {
      icon: undefined,
      title: t('state.empty.default.title'),
      description: t('state.empty.default.description'),
    },
  };
}

/* ==================== EmptyState 组件 ==================== */

interface EmptyStateProps {
  /** 场景类型 */
  scene?: EmptyScene;
  /** 自定义标题 */
  title?: string;
  /** 自定义描述 */
  description?: string;
  /** 操作按钮文字 */
  actionText?: string;
  /** 操作按钮回调 */
  onAction?: () => void;
  /** 自定义图标 */
  icon?: React.ReactNode;
}

/**
 * 统一空状态组件
 * 根据场景类型显示对应的图标、说明文字和操作建议
 */
export function EmptyState({ scene = 'default', title, description, actionText, onAction, icon }: EmptyStateProps) {
  const { t } = useTranslation();
  const config = getEmptyConfig(t)[scene];
  const displayIcon = icon || config.icon;

  return (
    <div style={{ textAlign: 'center', padding: '48px 0' }}>
      {displayIcon && <div style={{ marginBottom: 16 }}>{displayIcon}</div>}
      <Empty
        image={displayIcon ? Empty.PRESENTED_IMAGE_SIMPLE : Empty.PRESENTED_IMAGE_DEFAULT}
        description={
          <Space direction="vertical" size={4}>
            <Text strong style={{ fontSize: 15 }}>{title || config.title}</Text>
            <Text type="secondary">{description || config.description}</Text>
          </Space>
        }
      >
        {onAction && (
          <Button type="primary" icon={<PlusOutlined />} onClick={onAction}>
            {actionText || config.actionText || t('state.empty.start')}
          </Button>
        )}
      </Empty>
    </div>
  );
}

/* ==================== PageLoading 组件 ==================== */

interface PageLoadingProps {
  /** 加载提示文字 */
  tip?: string;
  /** 是否全屏居中 */
  fullScreen?: boolean;
}

/**
 * 统一页面加载组件
 */
export function PageLoading({ tip, fullScreen }: PageLoadingProps) {
  const { t } = useTranslation();
  const height = fullScreen ? 'calc(100vh - 200px)' : 400;
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: height }}>
      <Spin size="large" tip={tip || t('state.loading')}>
        <div style={{ padding: 50 }} />
      </Spin>
    </div>
  );
}
