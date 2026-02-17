/**
 * 主机列表页面
 * 展示所有受监控主机的概览信息，支持表格和卡片两种视图模式，
 * 提供按状态筛选和按主机名搜索功能。
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Card, Tag, Input, Select, Row, Col, Progress, Typography, Space, Button, Segmented } from 'antd';
import { CloudServerOutlined, AppstoreOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { hostService } from '../services/hosts';
import type { Host } from '../services/hosts';

const { Search } = Input;

/**
 * 主机列表组件
 * 支持分页查询、状态筛选、关键字搜索，以及表格/卡片视图切换
 */
export default function HostList() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  /** 状态筛选值：'online' | 'offline' | '' */
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');
  /** 视图模式：'table' 表格视图 | 'card' 卡片视图 */
  const [viewMode, setViewMode] = useState<string>('table');
  const navigate = useNavigate();

  /** 根据当前筛选条件从后端获取主机列表 */
  const fetchHosts = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const { data } = await hostService.list(params);
      setHosts(data.items || []);
      setTotal(data.total || 0);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  // 当分页或状态筛选变化时重新获取数据
  useEffect(() => { fetchHosts(); }, [page, pageSize, statusFilter]);

  /** 表格列定义 */
  const columns = [
    {
      title: '主机名', dataIndex: 'hostname', key: 'hostname',
      render: (text: string, record: Host) => (
        <Button type="link" onClick={() => navigate(`/hosts/${record.id}`)}>{text}</Button>
      ),
    },
    { title: 'IP 地址', dataIndex: 'ip_address', key: 'ip_address' },
    { title: '操作系统', dataIndex: 'os', key: 'os' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'online' ? 'success' : 'error'}>{s === 'online' ? '在线' : '离线'}</Tag>,
    },
    {
      title: 'CPU', key: 'cpu',
      render: (_: unknown, record: Host) => record.latest_metrics ? (
        <Progress percent={Math.round(record.latest_metrics.cpu_percent)} size="small" status={record.latest_metrics.cpu_percent > 90 ? 'exception' : 'normal'} />
      ) : '-',
    },
    {
      title: '内存', key: 'mem',
      render: (_: unknown, record: Host) => record.latest_metrics ? (
        <Progress percent={Math.round(record.latest_metrics.memory_percent)} size="small" status={record.latest_metrics.memory_percent > 90 ? 'exception' : 'normal'} />
      ) : '-',
    },
    {
      title: '磁盘', key: 'disk',
      render: (_: unknown, record: Host) => record.latest_metrics ? (
        <Progress percent={Math.round(record.latest_metrics.disk_percent)} size="small" status={record.latest_metrics.disk_percent > 90 ? 'exception' : 'normal'} />
      ) : '-',
    },
    {
      title: '标签', dataIndex: 'tags', key: 'tags',
      render: (tags: Record<string, boolean> | string[] | null) => {
        if (!tags) return '-';
        const arr = Array.isArray(tags) ? tags : Object.keys(tags);
        return arr.map(t => <Tag key={t}>{t}</Tag>);
      },
    },
  ];

  /** 卡片视图：以网格卡片形式展示主机基本信息和资源使用率 */
  const cardView = (
    <Row gutter={[16, 16]}>
      {hosts.map(host => (
        <Col key={host.id} xs={24} sm={12} md={8} lg={6}>
          <Card
            hoverable
            onClick={() => navigate(`/hosts/${host.id}`)}
            size="small"
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <CloudServerOutlined style={{ fontSize: 20 }} />
                <Typography.Text strong>{host.hostname}</Typography.Text>
                <Tag color={host.status === 'online' ? 'success' : 'error'}>{host.status === 'online' ? '在线' : '离线'}</Tag>
              </Space>
              <Typography.Text type="secondary">{host.ip_address}</Typography.Text>
              {host.latest_metrics && (
                <>
                  <div>CPU: <Progress percent={Math.round(host.latest_metrics.cpu_percent)} size="small" /></div>
                  <div>内存: <Progress percent={Math.round(host.latest_metrics.memory_percent)} size="small" /></div>
                </>
              )}
            </Space>
          </Card>
        </Col>
      ))}
    </Row>
  );

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Typography.Title level={4} style={{ margin: 0 }}>服务器列表</Typography.Title></Col>
        <Col>
          <Space>
            <Search placeholder="搜索主机名" onSearch={v => { setSearch(v); setPage(1); fetchHosts(); }} style={{ width: 200 }} allowClear />
            <Select placeholder="状态" allowClear style={{ width: 120 }} onChange={v => { setStatusFilter(v || ''); setPage(1); }}
              options={[{ label: '在线', value: 'online' }, { label: '离线', value: 'offline' }]} />
            <Segmented options={[
              { value: 'table', icon: <UnorderedListOutlined /> },
              { value: 'card', icon: <AppstoreOutlined /> },
            ]} value={viewMode} onChange={v => setViewMode(v as string)} />
          </Space>
        </Col>
      </Row>
      {viewMode === 'table' ? (
        <Table
          dataSource={hosts}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ current: page, pageSize, total, onChange: (p, ps) => { setPage(p); setPageSize(ps); } }}
        />
      ) : cardView}
    </div>
  );
}
