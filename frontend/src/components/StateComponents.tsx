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

const ERROR_CONFIG: Record<ErrorType, { icon: React.ReactNode; title: string; description: string }> = {
  network: {
    icon: <WifiOutlined style={{ fontSize: 48, color: '#faad14' }} />,
    title: '网络连接异常',
    description: '无法连接到服务器，请检查网络连接后重试。',
  },
  permission: {
    icon: <LockOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />,
    title: '没有访问权限',
    description: '您没有权限访问此资源，请联系管理员。',
  },
  server: {
    icon: <CloudServerOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />,
    title: '服务器错误',
    description: '服务器处理请求时出错，请稍后重试。',
  },
  notfound: {
    icon: <CloudServerOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />,
    title: '资源不存在',
    description: '请求的资源不存在或已被删除。',
  },
  unknown: {
    icon: <CloudServerOutlined style={{ fontSize: 48, color: '#faad14' }} />,
    title: '加载失败',
    description: '数据加载出错，请稍后重试。',
  },
};

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
  const errorType = type || classifyError(error);
  const config = ERROR_CONFIG[errorType];

  const content = (
    <Result
      icon={config.icon}
      title={title || config.title}
      subTitle={description || config.description}
      extra={
        onRetry ? (
          <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
            重新加载
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

const EMPTY_CONFIG: Record<EmptyScene, { icon: React.ReactNode; title: string; description: string; actionText?: string }> = {
  dashboard: {
    icon: <DashboardOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    title: '暂无监控数据',
    description: '还没有主机上报数据，请先添加主机并安装 Agent。',
    actionText: '添加主机',
  },
  servers: {
    icon: <CloudServerOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    title: '暂无服务器',
    description: '还没有服务器数据，请先添加主机并安装 Agent 开始监控。',
    actionText: '添加主机',
  },
  alerts: {
    icon: <AlertOutlined style={{ fontSize: 48, color: '#52c41a' }} />,
    title: '暂无告警',
    description: '当前没有任何告警，系统运行正常。您可以配置告警规则来监控关键指标。',
    actionText: '配置告警规则',
  },
  notifications: {
    icon: <BellOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    title: '暂无通知记录',
    description: '还没有发送过通知。当告警触发时，系统会自动通过配置的渠道发送通知。',
    actionText: '配置通知渠道',
  },
  reports: {
    icon: <FileTextOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    title: '暂无报告',
    description: '还没有生成过运维报告。您可以生成日报或周报来查看系统运行概况。',
    actionText: '生成报告',
  },
  topology: {
    icon: <ApartmentOutlined style={{ fontSize: 48, color: '#1890ff' }} />,
    title: '暂无拓扑数据',
    description: '还没有服务拓扑信息，请先添加服务并配置依赖关系。',
  },
  default: {
    icon: undefined,
    title: '暂无数据',
    description: '当前没有数据。',
  },
};

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
  const config = EMPTY_CONFIG[scene];
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
            {actionText || config.actionText || '开始'}
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
export function PageLoading({ tip = '加载中...', fullScreen }: PageLoadingProps) {
  const height = fullScreen ? 'calc(100vh - 200px)' : 400;
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: height }}>
      <Spin size="large" tip={tip}>
        <div style={{ padding: 50 }} />
      </Spin>
    </div>
  );
}
