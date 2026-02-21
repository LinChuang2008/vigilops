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

  /** 获取主机详情和监控指标 (Fetch host details and metrics)
   * 并行请求主机基本信息和时间范围内的历史指标数据
   * 支持不同时间范围：1h/6h/24h/7d，用于图表数据展示
   */
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

  /** 响应路由参数和时间范围变化 (React to route params and time range changes)
   * 当主机 ID 或时间范围切换时，重新获取对应的数据
   */
  useEffect(() => { fetchData(); }, [id, timeRange]);

  /** 设置自动刷新定时器 (Setup auto-refresh timer)
   * 每 30 秒自动刷新数据，保持监控数据的实时性
   * 组件卸载或依赖变化时清理定时器，防止内存泄漏
   */
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [id, timeRange]);

  if (loading && !host) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!host) return <Typography.Text>主机不存在</Typography.Text>;

  /** 提取时间轴标签数据 (Extract time axis labels)
   * 兼容后端可能返回的不同时间字段格式：recorded_at 或 timestamp
   * 转换为本地化时间格式，用作所有图表的 X 轴标签
   */
  const timestamps = metrics.map(m => {
    const ts = (m as Record<string, unknown>).recorded_at || m.timestamp;
    return ts ? new Date(ts as string).toLocaleTimeString() : '';
  });

  /** 生成通用折线图配置 (Generate common line chart options)
   * 标准化的 ECharts 折线图配置，包含面积填充、平滑曲线等
   * @param title 图表标题
   * @param series 数据系列数组，每项包含：名称、数据点、颜色
   * @returns ECharts 配置对象，支持多系列数据展示
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

  /** 网络累计流量图表配置 (Network cumulative traffic chart)
   * 展示发送和接收的总字节数，Y轴自动转换为KB显示
   * 适用于观察网络活跃度和数据传输总量趋势
   */
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

  /** 网络带宽速率图表配置 (Network bandwidth rate chart)
   * 展示实时上传/下载速率 (KB/s)，带面积填充效果
   * 用于监控网络实时负载和带宽利用情况，支持空值处理
   */
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

  /** 网络丢包率图表配置 (Network packet loss rate chart)
   * 监控网络质量指标，丢包率过高通常表示网络不稳定
   * 使用警告色(橙色)突出显示，支持空值默认为0处理
   */
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

      {/* 主机基本信息展示卡片 (Host basic information card) */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="主机名">{host.hostname}</Descriptions.Item>
          <Descriptions.Item label="IP 地址">{host.ip_address}</Descriptions.Item>
          <Descriptions.Item label="操作系统">{host.os}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {/* 在线状态用彩色标签区分：绿色在线/红色离线 */}
            <Tag color={host.status === 'online' ? 'success' : 'error'}>{host.status === 'online' ? '在线' : '离线'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="分组">{host.group || '-'}</Descriptions.Item>
          <Descriptions.Item label="最后心跳">{host.last_heartbeat ? new Date(host.last_heartbeat).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="标签">
            {/* 标签处理：兼容数组和对象两种数据格式 */}
            {host.tags ? (Array.isArray(host.tags) ? host.tags : Object.keys(host.tags)).map((t: string) => <Tag key={t}>{t}</Tag>) : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 监控图表网格布局 (Monitoring charts grid layout) */}
      <Row gutter={[16, 16]}>
        {/* CPU 使用率趋势图 - 蓝色主题 */}
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('CPU 使用率', [
              { name: 'CPU', data: metrics.map(m => m.cpu_percent), color: '#1677ff' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        {/* 内存使用率趋势图 - 绿色主题 */}
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('内存使用率', [
              { name: '内存', data: metrics.map(m => m.memory_percent), color: '#52c41a' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        {/* 磁盘使用率趋势图 - 橙色主题 */}
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('磁盘使用率', [
              { name: '磁盘', data: metrics.map(m => m.disk_percent), color: '#faad14' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        {/* 网络累计流量图 */}
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={netOption} style={{ height: 280 }} />
          </Card>
        </Col>
        {/* 网络带宽速率图 */}
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={netRateOption} style={{ height: 280 }} />
          </Card>
        </Col>
        {/* 网络丢包率图 */}
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={packetLossOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
