/**
 * 服务监控列表页面
 *
 * 支持按分类（中间件/业务系统/基础设施）和状态筛选，
 * 分类用彩色标签区分，表格展示服务状态、可用率等信息。
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table, Card, Tag, Typography, Progress, Button,
  Row, Col, Select, Space, Statistic, Segmented,
} from 'antd';
import {
  CloudServerOutlined, DatabaseOutlined, AppstoreOutlined, ApiOutlined,
} from '@ant-design/icons';
import { serviceService } from '../services/services';
import type { Service } from '../services/services';

const { Title } = Typography;

/** 分类配置：颜色、图标、中文名 */
const CATEGORY_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  middleware:      { label: '中间件',   color: 'purple',  icon: <DatabaseOutlined /> },
  business:       { label: '业务系统', color: 'blue',    icon: <AppstoreOutlined /> },
  infrastructure: { label: '基础设施', color: 'cyan',    icon: <CloudServerOutlined /> },
};

/** 获取分类标签 */
const CategoryTag = ({ category }: { category?: string }) => {
  const config = CATEGORY_CONFIG[category || ''] || { label: category || '未分类', color: 'default', icon: <ApiOutlined /> };
  return (
    <Tag color={config.color} icon={config.icon} style={{ marginRight: 0 }}>
      {config.label}
    </Tag>
  );
};

export default function ServiceList() {
  const [services, setServices] = useState<Service[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  /** 状态筛选 */
  const [statusFilter, setStatusFilter] = useState<string>('');
  /** 分类筛选 */
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const navigate = useNavigate();

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = { page, page_size: 50 };
        if (statusFilter) params.status = statusFilter;
        if (categoryFilter && categoryFilter !== 'all') params.category = categoryFilter;
        const { data } = await serviceService.list(params);
        setServices(data.items || []);
        setTotal(data.total || 0);
      } catch { /* ignore */ } finally { setLoading(false); }
    };
    fetch();
  }, [page, statusFilter, categoryFilter]);

  /** 统计各分类数量 */
  const categoryCounts = services.reduce<Record<string, number>>((acc, s) => {
    const cat = s.category || 'unknown';
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {});

  /** 统计各状态数量 */
  const healthyCount = services.filter(s => s.status === 'healthy' || s.status === 'up').length;
  const unhealthyCount = services.filter(s => s.status === 'unhealthy' || s.status === 'down').length;

  /** 表格列定义 */
  const columns = [
    {
      title: '服务名',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Service) => (
        <Button type="link" onClick={() => navigate(`/services/${record.id}`)}>
          {text}
        </Button>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (cat: string) => <CategoryTag category={cat} />,
    },
    {
      title: 'URL',
      key: 'url',
      ellipsis: true,
      render: (_: unknown, r: Service) => (
        <span style={{ color: '#999', fontSize: 13 }}>{r.target || r.url || '-'}</span>
      ),
    },
    {
      title: '检查类型',
      key: 'check_type',
      width: 100,
      render: (_: unknown, r: Service) => (
        <Tag>{(r.type || r.check_type || '')?.toUpperCase()}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (s: string) => {
        const isHealthy = s === 'healthy' || s === 'up';
        const isDegraded = s === 'degraded';
        return (
          <Tag color={isHealthy ? 'success' : isDegraded ? 'warning' : 'error'}>
            {isHealthy ? '健康' : isDegraded ? '降级' : '异常'}
          </Tag>
        );
      },
    },
    {
      title: '可用率',
      dataIndex: 'uptime_percent',
      key: 'uptime',
      width: 160,
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

  return (
    <div>
      {/* 顶部标题和统计 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>服务监控</Title>
        </Col>
        <Col>
          <Space size={24}>
            <Statistic title="总服务" value={total} valueStyle={{ fontSize: 20 }} />
            <Statistic
              title="健康"
              value={healthyCount}
              valueStyle={{ fontSize: 20, color: '#52c41a' }}
            />
            <Statistic
              title="异常"
              value={unhealthyCount}
              valueStyle={{ fontSize: 20, color: unhealthyCount > 0 ? '#ff4d4f' : '#d9d9d9' }}
            />
          </Space>
        </Col>
      </Row>

      {/* 分类切换 + 筛选器 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Segmented
            value={categoryFilter}
            onChange={(v) => { setCategoryFilter(v as string); setPage(1); }}
            options={[
              { label: `全部 (${total})`, value: 'all' },
              {
                label: (
                  <Space size={4}>
                    <DatabaseOutlined />
                    <span>中间件 ({categoryCounts.middleware || 0})</span>
                  </Space>
                ),
                value: 'middleware',
              },
              {
                label: (
                  <Space size={4}>
                    <AppstoreOutlined />
                    <span>业务系统 ({categoryCounts.business || 0})</span>
                  </Space>
                ),
                value: 'business',
              },
              {
                label: (
                  <Space size={4}>
                    <CloudServerOutlined />
                    <span>基础设施 ({categoryCounts.infrastructure || 0})</span>
                  </Space>
                ),
                value: 'infrastructure',
              },
            ]}
          />
        </Col>
        <Col>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => { setStatusFilter(v || ''); setPage(1); }}
            options={[
              { label: '健康', value: 'healthy' },
              { label: '异常', value: 'unhealthy' },
            ]}
          />
        </Col>
      </Row>

      {/* 服务列表 */}
      <Card>
        <Table
          dataSource={services}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: 50,
            total,
            onChange: (p) => setPage(p),
            showTotal: (t) => `共 ${t} 个服务`,
          }}
        />
      </Card>
    </div>
  );
}
