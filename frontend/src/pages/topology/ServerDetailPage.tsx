/**
 * 服务器详情页 - L2 钻取 (Server Detail Page - L2 Drill-down)
 *
 * 功能：在多服务器拓扑架构中，展示单台服务器的详细信息
 * 数据源：GET /api/v1/servers/:id (服务器信息 + 关联服务 + Nginx Upstream)
 * 路由参数：id - 服务器ID
 *
 * 页面结构：
 *   1. 服务器基本信息（Descriptions 组件）- IP、操作系统、状态等
 *   2. 服务列表（Table）- 该服务器上运行的所有服务，含状态、端口、类型
 *   3. Nginx Upstream 配置（Table）- 负载均衡上游配置信息
 *
 * 导航：从 ServerListPage (L1) 点击服务器卡片进入
 */
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography, Descriptions, Table, Tag, Card, Space, Button, Spin, message, Badge, Empty,
} from 'antd';
import {
  ArrowLeftOutlined, CloudServerOutlined, ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import api from '../../services/api';

const { Title, Text } = Typography;

interface ServerDetail {
  server: {
    id: number; hostname: string; ip_address: string | null; label: string | null;
    tags: Record<string, string> | null; status: string; last_seen: string | null;
    is_simulated: boolean; service_count: number; cpu_avg: number | null;
    mem_avg: number | null; created_at: string; updated_at: string;
  };
  services: {
    id: number; server_id: number; group_id: number; port: number | null;
    pid: number | null; status: string; cpu_percent: number; mem_mb: number;
    updated_at: string; group_name: string | null; group_category: string | null;
  }[];
  upstreams: {
    id: number; server_id: number; upstream_name: string; backend_address: string;
    weight: number; status: string; parsed_at: string;
  }[];
}

const statusTag = (status: string) => {
  const map: Record<string, { color: string; text: string }> = {
    online: { color: 'success', text: '在线' }, offline: { color: 'error', text: '离线' },
    unknown: { color: 'default', text: '未知' }, running: { color: 'success', text: '运行中' },
    stopped: { color: 'error', text: '已停止' }, error: { color: 'warning', text: '异常' },
    up: { color: 'success', text: 'UP' }, down: { color: 'error', text: 'DOWN' },
    backup: { color: 'warning', text: 'BACKUP' },
  };
  const cfg = map[status] || { color: 'default', text: status };
  return <Tag color={cfg.color}>{cfg.text}</Tag>;
};

const categoryColors: Record<string, string> = {
  web: 'orange', db: 'purple', cache: 'green', app: 'blue', mq: 'cyan', other: 'default',
};

export default function ServerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<ServerDetail | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/topology/servers/${id}`);
      setDetail(data);
    } catch {
      message.error('加载服务器详情失败');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  if (loading && !detail) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!detail) return <Empty description="未找到服务器" />;

  const { server, services, upstreams } = detail;

  const svcColumns: ColumnsType<ServerDetail['services'][0]> = [
    {
      title: '服务名', dataIndex: 'group_name',
      sorter: (a, b) => (a.group_name || '').localeCompare(b.group_name || ''),
      render: (v) => v || '—',
    },
    {
      title: '分类', dataIndex: 'group_category',
      render: (v: string | null) => v ? <Tag color={categoryColors[v] || 'default'}>{v}</Tag> : '—',
    },
    {
      title: '端口', dataIndex: 'port',
      sorter: (a, b) => (a.port || 0) - (b.port || 0),
      render: (v) => v ?? '—',
    },
    {
      title: 'PID', dataIndex: 'pid',
      render: (v) => v ?? '—',
    },
    {
      title: '状态', dataIndex: 'status',
      sorter: (a, b) => a.status.localeCompare(b.status),
      render: (v: string) => statusTag(v),
    },
    {
      title: 'CPU %', dataIndex: 'cpu_percent',
      sorter: (a, b) => a.cpu_percent - b.cpu_percent,
      render: (v: number) => {
        const color = v > 80 ? '#ff4d4f' : v > 50 ? '#faad14' : '#52c41a';
        return <Text style={{ color }}>{v.toFixed(1)}%</Text>;
      },
    },
    {
      title: '内存 (MB)', dataIndex: 'mem_mb',
      sorter: (a, b) => a.mem_mb - b.mem_mb,
      render: (v: number) => v.toFixed(1),
    },
  ];

  const upstreamColumns: ColumnsType<ServerDetail['upstreams'][0]> = [
    { title: 'Upstream 名称', dataIndex: 'upstream_name', sorter: (a, b) => a.upstream_name.localeCompare(b.upstream_name) },
    { title: '后端地址', dataIndex: 'backend_address' },
    { title: '权重', dataIndex: 'weight', sorter: (a, b) => a.weight - b.weight },
    { title: '状态', dataIndex: 'status', render: (v: string) => statusTag(v) },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/topology/servers')}>
          返回列表
        </Button>
        <Button icon={<ReloadOutlined />} onClick={fetchDetail} loading={loading}>刷新</Button>
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <CloudServerOutlined style={{ fontSize: 28 }} />
          <div>
            <Title level={4} style={{ margin: 0 }}>{server.hostname}</Title>
            <Text type="secondary">{server.ip_address || ''} {server.label ? `(${server.label})` : ''}</Text>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <Badge status={server.status === 'online' ? 'success' : server.status === 'offline' ? 'error' : 'default'}
              text={statusTag(server.status)} />
          </div>
        </div>

        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" bordered>
          <Descriptions.Item label="IP 地址">{server.ip_address || '—'}</Descriptions.Item>
          <Descriptions.Item label="标签">{server.label || '—'}</Descriptions.Item>
          <Descriptions.Item label="状态">{statusTag(server.status)}</Descriptions.Item>
          <Descriptions.Item label="服务数"><Tag color="blue">{server.service_count}</Tag></Descriptions.Item>
          <Descriptions.Item label="CPU 均值">{server.cpu_avg != null ? `${server.cpu_avg}%` : '—'}</Descriptions.Item>
          <Descriptions.Item label="内存均值">{server.mem_avg != null ? `${server.mem_avg} MB` : '—'}</Descriptions.Item>
          <Descriptions.Item label="最后上报">{server.last_seen ? new Date(server.last_seen).toLocaleString('zh-CN') : '—'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{new Date(server.created_at).toLocaleString('zh-CN')}</Descriptions.Item>
          <Descriptions.Item label="模拟数据">{server.is_simulated ? <Tag color="orange">是</Tag> : '否'}</Descriptions.Item>
          {server.tags && Object.keys(server.tags).length > 0 && (
            <Descriptions.Item label="标签" span={3}>
              {Object.entries(server.tags).map(([k, v]) => (
                <Tag key={k} color="geekblue">{k}: {v}</Tag>
              ))}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title={`运行的服务 (${services.length})`} style={{ marginBottom: 16 }}>
        {services.length === 0 ? (
          <Empty description="暂无服务" />
        ) : (
          <Table rowKey="id" columns={svcColumns} dataSource={services} pagination={false} size="small" />
        )}
      </Card>

      <Card title={`Nginx Upstream (${upstreams.length})`}>
        {upstreams.length === 0 ? (
          <Empty description="暂无 Nginx Upstream 配置" />
        ) : (
          <Table rowKey="id" columns={upstreamColumns} dataSource={upstreams} pagination={false} size="small" />
        )}
      </Card>
    </div>
  );
}
