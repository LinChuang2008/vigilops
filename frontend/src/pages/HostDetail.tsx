import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Descriptions, Tag, Spin, Typography, Select, Space } from 'antd';
import ReactECharts from 'echarts-for-react';
import { hostService } from '../services/hosts';
import type { Host, HostMetrics } from '../services/hosts';

export default function HostDetail() {
  const { id } = useParams<{ id: string }>();
  const [host, setHost] = useState<Host | null>(null);
  const [metrics, setMetrics] = useState<HostMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('1h');

  const fetchData = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [hostRes, metricsRes] = await Promise.all([
        hostService.get(id),
        hostService.getMetrics(id, { range: timeRange }),
      ]);
      setHost(hostRes.data);
      setMetrics(Array.isArray(metricsRes.data) ? metricsRes.data : []);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [id, timeRange]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [id, timeRange]);

  if (loading && !host) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!host) return <Typography.Text>主机不存在</Typography.Text>;

  const timestamps = metrics.map(m => new Date(m.timestamp).toLocaleTimeString());

  const lineOption = (title: string, series: { name: string; data: number[]; color: string }[]) => ({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    legend: { bottom: 0 },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, axisLabel: { formatter: '{value}%' } },
    series: series.map(s => ({ ...s, type: 'line' as const, smooth: true, areaStyle: { opacity: 0.1 } })),
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
  });

  const netOption = {
    title: { text: '网络流量', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    legend: { bottom: 0 },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => `${(v / 1024).toFixed(0)} KB` } },
    series: [
      { name: '发送', type: 'line' as const, data: metrics.map(m => m.net_bytes_sent), smooth: true, itemStyle: { color: '#1677ff' } },
      { name: '接收', type: 'line' as const, data: metrics.map(m => m.net_bytes_recv), smooth: true, itemStyle: { color: '#52c41a' } },
    ],
    grid: { top: 40, bottom: 60, left: 70, right: 20 },
  };

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Typography.Title level={4} style={{ margin: 0 }}>{host.hostname}</Typography.Title></Col>
        <Col>
          <Space>
            <Typography.Text type="secondary">时间范围:</Typography.Text>
            <Select value={timeRange} onChange={setTimeRange} style={{ width: 120 }}
              options={[
                { label: '1小时', value: '1h' },
                { label: '6小时', value: '6h' },
                { label: '24小时', value: '24h' },
                { label: '7天', value: '7d' },
              ]} />
          </Space>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="主机名">{host.hostname}</Descriptions.Item>
          <Descriptions.Item label="IP 地址">{host.ip_address}</Descriptions.Item>
          <Descriptions.Item label="操作系统">{host.os}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={host.status === 'online' ? 'success' : 'error'}>{host.status === 'online' ? '在线' : '离线'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="分组">{host.group || '-'}</Descriptions.Item>
          <Descriptions.Item label="最后心跳">{host.last_heartbeat ? new Date(host.last_heartbeat).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="标签">{host.tags?.map(t => <Tag key={t}>{t}</Tag>) || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('CPU 使用率', [
              { name: 'CPU', data: metrics.map(m => m.cpu_percent), color: '#1677ff' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('内存使用率', [
              { name: '内存', data: metrics.map(m => m.memory_percent), color: '#52c41a' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('磁盘使用率', [
              { name: '磁盘', data: metrics.map(m => m.disk_percent), color: '#faad14' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={netOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
