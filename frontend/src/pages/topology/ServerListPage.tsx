/**
 * 服务器列表页 - L1 全局视图 (Server List Page - L1 Overview)
 *
 * 功能：多服务器拓扑的入口页面，展示所有服务器的概览
 * 数据源：GET /api/v1/servers (服务器列表 + 统计信息)
 * 刷新策略：手动刷新按钮
 *
 * 页面结构：
 *   1. 统计卡片行 - 服务器总数、在线/离线/告警数量
 *   2. 搜索栏 - 按服务器名/IP搜索
 *   3. 服务器表格 - 名称、IP、OS、状态、服务数、操作
 *      点击行 → 钻取到 ServerDetailPage (L2)
 *
 * 状态颜色：online=green, offline=red, warning=orange
 */
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography, Table, Tag, Card, Row, Col, Statistic, Space, Button, Input, message,
} from 'antd';
import {
  CloudServerOutlined, CheckCircleOutlined, CloseCircleOutlined,
  QuestionCircleOutlined, ReloadOutlined, SearchOutlined, AppstoreOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title } = Typography;

interface ServerSummary {
  id: number;
  hostname: string;
  ip_address: string | null;
  label: string | null;
  tags: Record<string, string> | null;
  status: string;
  last_seen: string | null;
  is_simulated: boolean;
  service_count: number;
  cpu_avg: number | null;
  mem_avg: number | null;
  created_at: string;
  updated_at: string;
}

const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  online:  { color: 'success', icon: <CheckCircleOutlined />, text: '在线' },
  offline: { color: 'error',   icon: <CloseCircleOutlined />, text: '离线' },
  unknown: { color: 'default', icon: <QuestionCircleOutlined />, text: '未知' },
};

export default function ServerListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [servers, setServers] = useState<ServerSummary[]>([]);
  const [search, setSearch] = useState('');

  const fetchServers = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/topology/servers');
      setServers(data);
    } catch {
      message.error('加载服务器列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchServers(); }, [fetchServers]);

  const filtered = servers.filter(s =>
    !search ||
    s.hostname.toLowerCase().includes(search.toLowerCase()) ||
    s.ip_address?.includes(search) ||
    s.label?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: servers.length,
    online: servers.filter(s => s.status === 'online').length,
    offline: servers.filter(s => s.status === 'offline').length,
  };

  const columns: ColumnsType<ServerSummary> = [
    {
      title: '主机名',
      dataIndex: 'hostname',
      sorter: (a, b) => a.hostname.localeCompare(b.hostname),
      render: (text, record) => (
        <a onClick={() => navigate(`/topology/servers/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      sorter: (a, b) => (a.ip_address || '').localeCompare(b.ip_address || ''),
      render: (v) => v || '—',
    },
    {
      title: '标签',
      dataIndex: 'label',
      render: (v) => v || '—',
    },
    {
      title: '状态',
      dataIndex: 'status',
      sorter: (a, b) => a.status.localeCompare(b.status),
      filters: [
        { text: '在线', value: 'online' },
        { text: '离线', value: 'offline' },
        { text: '未知', value: 'unknown' },
      ],
      onFilter: (value, record) => record.status === value,
      render: (status: string) => {
        const cfg = statusConfig[status] || statusConfig.unknown;
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.text}</Tag>;
      },
    },
    {
      title: '服务数',
      dataIndex: 'service_count',
      sorter: (a, b) => a.service_count - b.service_count,
      render: (v) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: 'CPU 均值',
      dataIndex: 'cpu_avg',
      sorter: (a, b) => (a.cpu_avg || 0) - (b.cpu_avg || 0),
      render: (v: number | null) => v != null ? `${v}%` : '—',
    },
    {
      title: '内存均值 (MB)',
      dataIndex: 'mem_avg',
      sorter: (a, b) => (a.mem_avg || 0) - (b.mem_avg || 0),
      render: (v: number | null) => v != null ? `${v.toFixed(1)}` : '—',
    },
    {
      title: '最后上报',
      dataIndex: 'last_seen',
      sorter: (a, b) => (a.last_seen || '').localeCompare(b.last_seen || ''),
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '—',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <CloudServerOutlined style={{ marginRight: 8 }} />
          多服务器拓扑
        </Title>
        <Space>
          <Button icon={<AppstoreOutlined />} onClick={() => navigate('/topology/service-groups')}>
            服务组视图
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchServers} loading={loading}>刷新</Button>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="服务器总数" value={stats.total} prefix={<CloudServerOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="在线" value={stats.online} valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="离线" value={stats.offline} valueStyle={{ color: '#ff4d4f' }} prefix={<CloseCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      <Input
        placeholder="搜索主机名、IP 或标签…"
        prefix={<SearchOutlined />}
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
      />

      <Table
        rowKey="id"
        columns={columns}
        dataSource={filtered}
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: t => `共 ${t} 台` }}
        size="middle"
        onRow={(record) => ({
          onClick: () => navigate(`/topology/servers/${record.id}`),
          style: { cursor: 'pointer' },
        })}
      />
    </div>
  );
}
