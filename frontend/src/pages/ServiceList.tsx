import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Card, Tag, Typography, Progress, Button, Row, Col, Select, Space } from 'antd';
import { serviceService } from '../services/services';
import type { Service } from '../services/services';

export default function ServiceList() {
  const [services, setServices] = useState<Service[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = { page, page_size: 20 };
        if (statusFilter) params.status = statusFilter;
        const { data } = await serviceService.list(params);
        setServices(data.items || []);
        setTotal(data.total || 0);
      } catch { /* ignore */ } finally { setLoading(false); }
    };
    fetch();
  }, [page, statusFilter]);

  const columns = [
    {
      title: '服务名', dataIndex: 'name', key: 'name',
      render: (text: string, record: Service) => <Button type="link" onClick={() => navigate(`/services/${record.id}`)}>{text}</Button>,
    },
    { title: 'URL', key: 'url', ellipsis: true, render: (_: unknown, r: Service) => r.target || r.url || '-' },
    { title: '检查类型', key: 'check_type', render: (_: unknown, r: Service) => <Tag>{(r.type || r.check_type || '')?.toUpperCase()}</Tag> },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => {
        const isHealthy = s === 'healthy' || s === 'up';
        const isDegraded = s === 'degraded';
        return <Tag color={isHealthy ? 'success' : isDegraded ? 'warning' : 'error'}>{isHealthy ? '健康' : isDegraded ? '降级' : '异常'}</Tag>;
      },
    },
    {
      title: '可用率', dataIndex: 'uptime_percent', key: 'uptime',
      render: (v: number) => <Progress percent={v != null ? Math.round(v * 100) / 100 : 0} size="small" status={v >= 99 ? 'success' : v >= 95 ? 'normal' : 'exception'} />,
    },
    {
      title: '最后检查', dataIndex: 'last_check', key: 'last_check',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Typography.Title level={4} style={{ margin: 0 }}>服务监控</Typography.Title></Col>
        <Col>
          <Space>
            <Select placeholder="状态筛选" allowClear style={{ width: 120 }} onChange={v => { setStatusFilter(v || ''); setPage(1); }}
              options={[{ label: '健康', value: 'healthy' }, { label: '异常', value: 'unhealthy' }]} />
          </Space>
        </Col>
      </Row>
      <Card>
        <Table dataSource={services} columns={columns} rowKey="id" loading={loading}
          pagination={{ current: page, pageSize: 20, total, onChange: p => setPage(p) }} />
      </Card>
    </div>
  );
}
