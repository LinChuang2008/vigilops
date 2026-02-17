/**
 * 服务监控列表页面
 *
 * 按服务器分组展示服务，每个服务器一个折叠卡片，内含该服务器上的所有服务。
 * 支持按分类（中间件/业务系统）和状态筛选。
 * 单台服务器时平铺显示，多台时分组显示。
 */
import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table, Card, Tag, Typography, Progress, Button,
  Row, Col, Select, Space, Statistic, Collapse, Badge, Empty,
} from 'antd';
import {
  CloudServerOutlined, DatabaseOutlined, AppstoreOutlined,
  ApiOutlined, DesktopOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { serviceService } from '../services/services';
import type { Service } from '../services/services';

const { Title, Text } = Typography;

/* ==================== 类型定义 ==================== */

/** 主机分组数据 */
interface HostGroup {
  host_id: number;
  hostname: string;
  ip: string;
  host_status: string;
  services: ServiceItem[];
}

/** 带主机信息的服务 */
interface ServiceItem extends Service {
  host_info?: { id: number; hostname: string; ip: string; status: string } | null;
}

/* ==================== 分类配置 ==================== */

const CATEGORY_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  middleware:      { label: '中间件',   color: 'purple', icon: <DatabaseOutlined /> },
  business:       { label: '业务系统', color: 'blue',   icon: <AppstoreOutlined /> },
  infrastructure: { label: '基础设施', color: 'cyan',   icon: <CloudServerOutlined /> },
};

/** 分类标签组件 */
const CategoryTag = ({ category }: { category?: string }) => {
  const config = CATEGORY_CONFIG[category || ''] || { label: category || '未分类', color: 'default', icon: <ApiOutlined /> };
  return <Tag color={config.color} icon={config.icon} style={{ marginRight: 0 }}>{config.label}</Tag>;
};

/** 状态颜色 */
const statusColor = (s: string) => {
  if (s === 'healthy' || s === 'up') return 'success';
  if (s === 'degraded') return 'warning';
  return 'error';
};
const statusText = (s: string) => {
  if (s === 'healthy' || s === 'up') return '健康';
  if (s === 'degraded') return '降级';
  return '异常';
};

/* ==================== 组件 ==================== */

export default function ServiceList() {
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [hostGroups, setHostGroups] = useState<HostGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const navigate = useNavigate();

  /** 拉取数据（group_by_host） */
  const fetchData = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: 1, page_size: 100, group_by_host: true };
      if (statusFilter) params.status = statusFilter;
      if (categoryFilter) params.category = categoryFilter;
      const { data } = await serviceService.list(params);
      setServices(data.items || []);
      setTotal(data.total || 0);
      setHostGroups(data.host_groups || []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [statusFilter, categoryFilter]); // eslint-disable-line

  /** 统计 */
  const stats = useMemo(() => {
    const healthy = services.filter(s => s.status === 'healthy' || s.status === 'up').length;
    const unhealthy = services.filter(s => s.status === 'unhealthy' || s.status === 'down').length;
    const mw = services.filter(s => s.category === 'middleware').length;
    const biz = services.filter(s => s.category === 'business').length;
    return { healthy, unhealthy, mw, biz, hosts: hostGroups.length };
  }, [services, hostGroups]);

  /** 表格列定义 */
  const columns = [
    {
      title: '服务名',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: ServiceItem) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => navigate(`/services/${record.id}`)}>
          {text}
        </Button>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 110,
      render: (cat: string) => <CategoryTag category={cat} />,
    },
    {
      title: '目标地址',
      key: 'url',
      ellipsis: true,
      render: (_: unknown, r: ServiceItem) => (
        <Text type="secondary" style={{ fontSize: 13 }}>{r.target || r.url || '-'}</Text>
      ),
    },
    {
      title: '类型',
      key: 'check_type',
      width: 80,
      render: (_: unknown, r: ServiceItem) => (
        <Tag>{(r.type || r.check_type || '')?.toUpperCase()}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (s: string) => <Tag color={statusColor(s)}>{statusText(s)}</Tag>,
    },
    {
      title: '可用率 (24h)',
      dataIndex: 'uptime_percent',
      key: 'uptime',
      width: 150,
      render: (v: number) => (
        <Progress
          percent={v != null ? Math.round(v * 100) / 100 : 0}
          size="small"
          status={v >= 99 ? 'success' : v >= 95 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '最后检查',
      dataIndex: 'last_check',
      key: 'last_check',
      width: 170,
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ];

  /** 渲染单个主机的服务表格 */
  const renderServiceTable = (items: ServiceItem[]) => (
    <Table
      dataSource={items}
      columns={columns}
      rowKey="id"
      size="small"
      pagination={false}
    />
  );

  /** 渲染主机卡片头部 */
  const renderHostHeader = (group: HostGroup) => {
    const healthyCount = group.services.filter(s => s.status === 'up' || s.status === 'healthy').length;
    const totalCount = group.services.length;
    const mwCount = group.services.filter(s => s.category === 'middleware').length;
    const bizCount = group.services.filter(s => s.category === 'business').length;
    const isOnline = group.host_status === 'online';

    return (
      <Space size={16} style={{ width: '100%' }}>
        <Space>
          <DesktopOutlined style={{ fontSize: 18, color: isOnline ? '#52c41a' : '#ff4d4f' }} />
          <span style={{ fontWeight: 600, fontSize: 15 }}>{group.hostname}</span>
          {group.ip && <Text type="secondary">({group.ip})</Text>}
          <Tag color={isOnline ? 'success' : 'error'}>{isOnline ? '在线' : '离线'}</Tag>
        </Space>
        <Space size={12}>
          <Badge
            count={`${healthyCount}/${totalCount}`}
            style={{ backgroundColor: healthyCount === totalCount ? '#52c41a' : '#faad14' }}
          />
          {mwCount > 0 && <Tag color="purple">中间件 {mwCount}</Tag>}
          {bizCount > 0 && <Tag color="blue">业务 {bizCount}</Tag>}
        </Space>
      </Space>
    );
  };

  const isSingleHost = hostGroups.length <= 1;

  return (
    <div>
      {/* 标题 + 统计 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space size={16}>
            <Title level={4} style={{ margin: 0 }}>服务监控</Title>
            <Tag icon={<DesktopOutlined />} color="default">{stats.hosts} 台服务器</Tag>
          </Space>
        </Col>
        <Col>
          <Space size={20}>
            <Statistic title="总服务" value={total} valueStyle={{ fontSize: 18 }} />
            <Statistic
              title="中间件"
              value={stats.mw}
              prefix={<DatabaseOutlined />}
              valueStyle={{ fontSize: 18, color: '#722ed1' }}
            />
            <Statistic
              title="业务系统"
              value={stats.biz}
              prefix={<AppstoreOutlined />}
              valueStyle={{ fontSize: 18, color: '#1890ff' }}
            />
            <Statistic
              title="健康"
              value={stats.healthy}
              valueStyle={{ fontSize: 18, color: '#52c41a' }}
            />
            <Statistic
              title="异常"
              value={stats.unhealthy}
              valueStyle={{ fontSize: 18, color: stats.unhealthy > 0 ? '#ff4d4f' : '#d9d9d9' }}
            />
          </Space>
        </Col>
      </Row>

      {/* 筛选器 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Select
              placeholder="服务分类"
              allowClear
              style={{ width: 130 }}
              value={categoryFilter}
              onChange={(v) => setCategoryFilter(v || undefined)}
              options={[
                { label: '🗄️ 中间件', value: 'middleware' },
                { label: '📦 业务系统', value: 'business' },
                { label: '☁️ 基础设施', value: 'infrastructure' },
              ]}
            />
            <Select
              placeholder="运行状态"
              allowClear
              style={{ width: 120 }}
              value={statusFilter}
              onChange={(v) => setStatusFilter(v || undefined)}
              options={[
                { label: '✅ 健康', value: 'up' },
                { label: '❌ 异常', value: 'down' },
              ]}
            />
          </Space>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        </Col>
      </Row>

      {/* 服务列表 */}
      {loading ? (
        <Card loading />
      ) : hostGroups.length === 0 ? (
        <Card><Empty description="暂无服务" /></Card>
      ) : isSingleHost ? (
        /* 单台服务器：直接平铺 */
        <Card
          title={renderHostHeader(hostGroups[0])}
          size="small"
          styles={{ header: { background: '#fafafa' } }}
        >
          {renderServiceTable(hostGroups[0].services)}
        </Card>
      ) : (
        /* 多台服务器：折叠分组 */
        <Collapse
          defaultActiveKey={hostGroups.map(g => String(g.host_id))}
          items={hostGroups.map(group => ({
            key: String(group.host_id),
            label: renderHostHeader(group),
            children: renderServiceTable(group.services),
            style: { marginBottom: 12, borderRadius: 8, overflow: 'hidden' },
          }))}
          style={{ background: 'transparent' }}
        />
      )}
    </div>
  );
}
