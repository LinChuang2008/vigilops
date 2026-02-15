import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Typography, Tag, Table, Spin } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import api from '../services/api';

const { Title } = Typography;

interface DashboardData {
  hosts: { total: number; online: number; offline: number; items: Array<{ id: string; hostname: string; status: string; latest_metrics?: { cpu_percent: number; memory_percent: number } }> };
  services: { total: number; healthy: number; unhealthy: number };
  alerts: { total: number; firing: number; items: Array<{ id: string; title: string; severity: string; status: string; fired_at: string }> };
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [hostsRes, servicesRes, alertsRes] = await Promise.all([
          api.get('/hosts', { params: { page_size: 100 } }),
          api.get('/services', { params: { page_size: 100 } }),
          api.get('/alerts', { params: { page_size: 10, status: 'firing' } }),
        ]);
        const hosts = hostsRes.data;
        const services = servicesRes.data;
        const alerts = alertsRes.data;
        setData({
          hosts: {
            total: hosts.total,
            online: hosts.items?.filter((h: { status: string }) => h.status === 'online').length || 0,
            offline: hosts.items?.filter((h: { status: string }) => h.status === 'offline').length || 0,
            items: hosts.items || [],
          },
          services: {
            total: services.total,
            healthy: services.items?.filter((s: { status: string }) => s.status === 'healthy' || s.status === 'up').length || 0,
            unhealthy: services.items?.filter((s: { status: string }) => s.status !== 'healthy' && s.status !== 'up').length || 0,
          },
          alerts: {
            total: alerts.total,
            firing: alerts.items?.filter((a: { status: string }) => a.status === 'firing').length || 0,
            items: alerts.items || [],
          },
        });
      } catch {
        // API might not be accessible yet
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const d = data || { hosts: { total: 0, online: 0, offline: 0, items: [] }, services: { total: 0, healthy: 0, unhealthy: 0 }, alerts: { total: 0, firing: 0, items: [] } };

  const cpuData = d.hosts.items
    .filter(h => h.latest_metrics)
    .map(h => ({ name: h.hostname, value: h.latest_metrics!.cpu_percent }));

  const memData = d.hosts.items
    .filter(h => h.latest_metrics)
    .map(h => ({ name: h.hostname, value: h.latest_metrics!.memory_percent }));

  const barOption = (title: string, items: { name: string; value: number }[], color: string) => ({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: items.map(i => i.name), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{ type: 'bar' as const, data: items.map(i => i.value), itemStyle: { color } }],
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
  });

  const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };

  return (
    <div>
      <Title level={4}>系统概览</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="服务器总数" value={d.hosts.total} prefix={<CloudServerOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag icon={<CheckCircleOutlined />} color="success">在线 {d.hosts.online}</Tag>
              <Tag icon={<CloseCircleOutlined />} color="error">离线 {d.hosts.offline}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="服务总数" value={d.services.total} prefix={<ApiOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {d.services.healthy}</Tag>
              <Tag color="error">异常 {d.services.unhealthy}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="活跃告警" value={d.alerts.firing} prefix={<AlertOutlined />} valueStyle={{ color: d.alerts.firing > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="CPU 使用率">
            {cpuData.length > 0 ? (
              <ReactECharts option={barOption('', cpuData, '#1677ff')} style={{ height: 250 }} />
            ) : (
              <Typography.Text type="secondary">暂无数据</Typography.Text>
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="内存使用率">
            {memData.length > 0 ? (
              <ReactECharts option={barOption('', memData, '#52c41a')} style={{ height: 250 }} />
            ) : (
              <Typography.Text type="secondary">暂无数据</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="最新告警" style={{ marginTop: 16 }}>
        <Table
          dataSource={d.alerts.items}
          rowKey="id"
          pagination={false}
          size="small"
          columns={[
            { title: '标题', dataIndex: 'title', key: 'title' },
            {
              title: '严重级别', dataIndex: 'severity', key: 'severity',
              render: (s: string) => <Tag color={severityColor[s] || 'default'}>{s}</Tag>,
            },
            { title: '触发时间', dataIndex: 'fired_at', key: 'fired_at', render: (t: string) => new Date(t).toLocaleString() },
          ]}
          locale={{ emptyText: '暂无活跃告警' }}
        />
      </Card>
    </div>
  );
}
