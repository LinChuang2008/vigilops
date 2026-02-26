/**
 * 服务详情页面
 * 展示单个服务的基本信息、响应时间趋势图、可用率散点图和检查历史记录。
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Descriptions, Tag, Spin, Typography, Table, Row, Col } from 'antd';
import ReactECharts from '../components/ThemedECharts';
import { serviceService } from '../services/services';
import type { Service, ServiceCheck } from '../services/services';

/**
 * 服务详情组件
 * 通过路由参数 id 获取服务信息和检查记录，渲染响应时间和可用率图表
 */
export default function ServiceDetail() {
  const { id } = useParams<{ id: string }>();
  const [service, setService] = useState<Service | null>(null);
  const [checks, setChecks] = useState<ServiceCheck[]>([]);
  const [loading, setLoading] = useState(true);

  /** 获取服务详情和检查历史 (Fetch service details and check history)
   * 并行请求服务基本信息和最近100条检查记录
   * 兼容后端返回格式：数组或分页对象结构
   */
  useEffect(() => {
    if (!id) return;
    const fetch = async () => {
      setLoading(true);
      try {
        const [sRes, cRes] = await Promise.all([
          serviceService.get(id),
          serviceService.getChecks(id, { page_size: 100 }),
        ]);
        setService(sRes.data);
        // 兼容数组和分页对象两种返回格式
        const items = Array.isArray(cRes.data) ? cRes.data : (cRes.data as { items?: ServiceCheck[] }).items || [];
        setChecks(items);
      } catch { /* ignore */ } finally { setLoading(false); }
    };
    fetch();
  }, [id]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!service) return <Typography.Text>服务不存在</Typography.Text>;

  /** 判断服务状态是否为健康 (Check if service status is healthy)
   * 兼容 'up' 和 'healthy' 两种健康状态标识
   * @param s 服务状态字符串
   * @returns 是否为健康状态
   */
  const isUp = (s: string) => s === 'up' || s === 'healthy';

  /** 检查记录时间排序和格式化 (Sort and format check records by time)
   * 按检查时间升序排列，确保图表时间轴正确显示
   * 提取本地化时间标签用于图表X轴
   */
  const sorted = [...checks].sort((a, b) => new Date(a.checked_at).getTime() - new Date(b.checked_at).getTime());
  const timestamps = sorted.map(c => new Date(c.checked_at).toLocaleTimeString());

  /** 响应时间趋势图配置 (Response time trend chart options)
   * 平滑折线图显示服务响应时间变化，带面积填充效果
   * 用于分析服务性能趋势和异常波动
   */
  const rtOption = {
    title: { text: '响应时间 (ms)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const },
    series: [{ type: 'line' as const, data: sorted.map(c => c.response_time_ms), smooth: true, itemStyle: { color: '#1677ff' }, areaStyle: { opacity: 0.1 } }],
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
  };

  /** 可用率散点图配置 (Uptime scatter plot options)
   * 散点图显示服务可用性：1=可用，0=不可用
   * 直观展示服务稳定性和故障时间点分布
   */
  const uptimeOption = {
    title: { text: '可用率趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, min: 0, max: 1 },
    series: [{
      type: 'scatter' as const,
      data: sorted.map(c => isUp(c.status) ? 1 : 0),
      itemStyle: { color: '#52c41a' },
      symbolSize: 8,
    }],
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
  };

  /** 字段兼容性处理 (Field compatibility handling)
   * 兼容后端不同版本可能使用的字段名：target/url 和 type/check_type
   */
  const serviceUrl = service.target || service.url || '-';
  const serviceType = service.type || service.check_type || '-';
  const serviceIsUp = isUp(service.status);

  /** 最近检查时间计算 (Calculate latest check time)
   * 从检查记录中获取最新的检查时间，用于基本信息展示
   */
  const lastCheckTime = checks.length > 0
    ? new Date(checks[0].checked_at).toLocaleString()
    : '-';

  return (
    <div>
      <Typography.Title level={4}>{service.name}</Typography.Title>

      {/* 服务基本信息展示卡片 (Service basic information card) */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="URL">{serviceUrl}</Descriptions.Item>
          <Descriptions.Item label="检查类型"><Tag>{serviceType.toUpperCase()}</Tag></Descriptions.Item>
          <Descriptions.Item label="状态">
            {/* 状态标签：健康=绿色，异常=红色 */}
            <Tag color={serviceIsUp ? 'success' : 'error'}>{serviceIsUp ? '健康' : '异常'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="可用率">{service.uptime_percent != null ? `${service.uptime_percent}%` : '-'}</Descriptions.Item>
          <Descriptions.Item label="最后检查">{lastCheckTime}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 性能监控图表区域 (Performance monitoring charts) */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          {/* 响应时间趋势图 */}
          <Card><ReactECharts option={rtOption} style={{ height: 280 }} /></Card>
        </Col>
        <Col xs={24} md={12}>
          {/* 可用率散点图 */}
          <Card><ReactECharts option={uptimeOption} style={{ height: 280 }} /></Card>
        </Col>
      </Row>

      {/* 检查历史记录详情表格 (Check history details table) */}
      <Card title="检查历史">
        <Table dataSource={checks} rowKey="id" size="small"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={isUp(s) ? 'success' : 'error'}>{s}</Tag> },
            { title: '响应时间', dataIndex: 'response_time_ms', render: (v: number) => `${v} ms` },
            { title: '状态码', dataIndex: 'status_code', render: (v: number | null) => v || '-' },
            { title: '错误', dataIndex: 'error', render: (v: string | null) => v || '-', ellipsis: true },
            { title: '检查时间', dataIndex: 'checked_at', render: (t: string) => new Date(t).toLocaleString() },
          ]} />
      </Card>
    </div>
  );
}
