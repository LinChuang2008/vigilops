/**
 * 主机详情页面
 * 展示单台主机的基本信息和性能监控图表，包括 CPU、内存、磁盘使用率，
 * 网络流量、网络带宽和丢包率等指标，支持时间范围切换，每 30 秒自动刷新。
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Descriptions, Tag, Spin, Typography, Select, Space } from 'antd';
import ReactECharts from 'echarts-for-react';
import { hostService } from '../services/hosts';
import type { Host, HostMetrics } from '../services/hosts';

/**
 * 主机详情组件
 * 通过路由参数 id 获取主机信息和历史指标数据，渲染多维度监控图表
 */
export default function HostDetail() {
  const { id } = useParams<{ id: string }>();
  const [host, setHost] = useState<Host | null>(null);
  const [metrics, setMetrics] = useState<HostMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  /** 时间范围选择：1h / 6h / 24h / 7d */
  const [timeRange, setTimeRange] = useState('1h');

  /** 并行获取主机基本信息和指标数据 */
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

  // 每 30 秒自动刷新数据
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [id, timeRange]);

  if (loading && !host) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!host) return <Typography.Text>主机不存在</Typography.Text>;

  // 提取时间轴标签，兼容 recorded_at 和 timestamp 两种字段
  const timestamps = metrics.map(m => {
    const ts = (m as Record<string, unknown>).recorded_at || m.timestamp;
    return ts ? new Date(ts as string).toLocaleTimeString() : '';
  });

  /**
   * 生成折线图配置
   * @param title 图表标题
   * @param series 数据系列（名称、数据、颜色）
   */
  const lineOption = (title: string, series: { name: string; data: number[]; color: string }[]) => ({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    legend: { bottom: 0 },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, axisLabel: { formatter: '{value}%' } },
    series: series.map(s => ({ ...s, type: 'line' as const, smooth: true, areaStyle: { opacity: 0.1 } })),
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
  });

  /** 网络累计流量图表配置 */
  const netOption = {
    title: { text: '网络流量（累计）', left: 'center', textStyle: { fontSize: 14 } },
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

  /** 网络带宽速率图表配置（KB/s） */
  const netRateOption = {
    title: { text: '网络带宽 (KB/s)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    legend: { bottom: 0 },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, axisLabel: { formatter: '{value} KB/s' } },
    series: [
      { name: '上传', type: 'line' as const, data: metrics.map(m => m.net_send_rate_kb ?? 0), smooth: true, areaStyle: { opacity: 0.1 }, itemStyle: { color: '#1677ff' } },
      { name: '下载', type: 'line' as const, data: metrics.map(m => m.net_recv_rate_kb ?? 0), smooth: true, areaStyle: { opacity: 0.1 }, itemStyle: { color: '#52c41a' } },
    ],
    grid: { top: 40, bottom: 60, left: 60, right: 20 },
  };

  /** 丢包率图表配置 */
  const packetLossOption = {
    title: { text: '丢包率', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '丢包率', type: 'line' as const, data: metrics.map(m => m.net_packet_loss_rate ?? 0), smooth: true, areaStyle: { opacity: 0.15 }, itemStyle: { color: '#faad14' } },
    ],
    grid: { top: 40, bottom: 40, left: 50, right: 20 },
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

      {/* 主机基本信息卡片 */}
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
          <Descriptions.Item label="标签">{host.tags ? (Array.isArray(host.tags) ? host.tags : Object.keys(host.tags)).map((t: string) => <Tag key={t}>{t}</Tag>) : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 监控图表网格 */}
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
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={netRateOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={packetLossOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
