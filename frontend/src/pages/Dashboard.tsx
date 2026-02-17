/**
 * 仪表盘页面
 *
 * 系统总览页，展示服务器、服务、数据库、告警等核心指标统计卡片，
 * 以及 CPU/内存使用率、网络带宽、丢包率的柱状图，日志级别分布饼图，
 * 和最新告警列表。数据每 30 秒自动刷新。
 */
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
import { fetchLogStats } from '../services/logs';
import type { LogStats } from '../services/logs';
import { databaseService } from '../services/databases';
import type { DatabaseItem } from '../services/databases';
import { DatabaseOutlined } from '@ant-design/icons';

const { Title } = Typography;

/** 仪表盘聚合数据结构 */
interface DashboardData {
  /** 服务器概况 */
  hosts: {
    total: number;
    online: number;
    offline: number;
    /** 服务器列表（含最新指标） */
    items: Array<{
      id: string;
      hostname: string;
      status: string;
      latest_metrics?: {
        cpu_percent: number;
        memory_percent: number;
        net_send_rate_kb?: number;
        net_recv_rate_kb?: number;
        net_packet_loss_rate?: number;
      };
    }>;
  };
  /** 服务概况 */
  services: { total: number; healthy: number; unhealthy: number };
  /** 告警概况 */
  alerts: {
    total: number;
    firing: number;
    items: Array<{ id: string; title: string; severity: string; status: string; fired_at: string }>;
  };
}

/**
 * 仪表盘页面组件
 *
 * 页面加载时并行请求服务器、服务、告警数据，并定时轮询刷新。
 */
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  /** 日志统计数据（按级别分布） */
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  /** 数据库列表 */
  const [dbItems, setDbItems] = useState<DatabaseItem[]>([]);

  useEffect(() => {
    /** 并行获取各模块数据并聚合为仪表盘所需格式 */
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
        // 获取最近 1 小时日志统计
        try {
          const stats = await fetchLogStats('1h');
          setLogStats(stats);
        } catch { /* ignore */ }
        // 获取数据库列表
        try {
          const dbRes = await databaseService.list();
          setDbItems(dbRes.data.databases || []);
        } catch { /* ignore */ }
      } catch {
        // API 可能尚未就绪
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    // 每 30 秒自动刷新
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  /** 数据兜底：确保即使接口未返回数据也不会报错 */
  const d = data || { hosts: { total: 0, online: 0, offline: 0, items: [] }, services: { total: 0, healthy: 0, unhealthy: 0 }, alerts: { total: 0, firing: 0, items: [] } };

  /** 提取各服务器 CPU 使用率数据 */
  const cpuData = d.hosts.items
    .filter(h => h.latest_metrics)
    .map(h => ({ name: h.hostname, value: h.latest_metrics!.cpu_percent }));

  /** 提取各服务器内存使用率数据 */
  const memData = d.hosts.items
    .filter(h => h.latest_metrics)
    .map(h => ({ name: h.hostname, value: h.latest_metrics!.memory_percent }));

  /** 生成 ECharts 柱状图配置 */
  const barOption = (title: string, items: { name: string; value: number }[], color: string) => ({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: items.map(i => i.name), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{ type: 'bar' as const, data: items.map(i => i.value), itemStyle: { color } }],
    grid: { top: 40, bottom: 60, left: 50, right: 20 },
  });

  /** 告警严重级别对应颜色映射 */
  const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };

  return (
    <div>
      <Title level={4}>系统概览</Title>

      {/* 核心指标统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="服务器总数" value={d.hosts.total} prefix={<CloudServerOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag icon={<CheckCircleOutlined />} color="success">在线 {d.hosts.online}</Tag>
              <Tag icon={<CloseCircleOutlined />} color="error">离线 {d.hosts.offline}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="服务总数" value={d.services.total} prefix={<ApiOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {d.services.healthy}</Tag>
              <Tag color="error">异常 {d.services.unhealthy}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="数据库" value={dbItems.length} prefix={<DatabaseOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {dbItems.filter(d => d.status === 'healthy').length}</Tag>
              <Tag color="error">异常 {dbItems.filter(d => d.status !== 'healthy' && d.status !== 'unknown').length}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="活跃告警" value={d.alerts.firing} prefix={<AlertOutlined />} valueStyle={{ color: d.alerts.firing > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
      </Row>

      {/* CPU / 内存使用率图表 */}
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

      {/* 网络带宽与丢包率图表 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="网络带宽 (KB/s)">
            {(() => {
              const netHosts = d.hosts.items.filter(h => h.latest_metrics?.net_send_rate_kb != null);
              if (netHosts.length === 0) return <Typography.Text type="secondary">暂无数据</Typography.Text>;
              return (
                <ReactECharts style={{ height: 250 }} option={{
                  tooltip: { trigger: 'axis' as const },
                  legend: { bottom: 0 },
                  xAxis: { type: 'category' as const, data: netHosts.map(h => h.hostname), axisLabel: { rotate: 30 } },
                  yAxis: { type: 'value' as const, axisLabel: { formatter: '{value} KB/s' } },
                  series: [
                    { name: '上传', type: 'bar' as const, data: netHosts.map(h => h.latest_metrics!.net_send_rate_kb ?? 0), itemStyle: { color: '#1677ff' } },
                    { name: '下载', type: 'bar' as const, data: netHosts.map(h => h.latest_metrics!.net_recv_rate_kb ?? 0), itemStyle: { color: '#52c41a' } },
                  ],
                  grid: { top: 20, bottom: 60, left: 60, right: 20 },
                }} />
              );
            })()}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="丢包率">
            {(() => {
              const netHosts = d.hosts.items.filter(h => h.latest_metrics?.net_packet_loss_rate != null);
              if (netHosts.length === 0) return <Typography.Text type="secondary">暂无数据</Typography.Text>;
              return (
                <ReactECharts style={{ height: 250 }} option={{
                  tooltip: { trigger: 'axis' as const },
                  xAxis: { type: 'category' as const, data: netHosts.map(h => h.hostname), axisLabel: { rotate: 30 } },
                  yAxis: { type: 'value' as const, axisLabel: { formatter: '{value}%' } },
                  series: [{ name: '丢包率', type: 'bar' as const, data: netHosts.map(h => h.latest_metrics!.net_packet_loss_rate ?? 0), itemStyle: { color: '#faad14' } }],
                  grid: { top: 20, bottom: 60, left: 50, right: 20 },
                }} />
              );
            })()}
          </Card>
        </Col>
      </Row>

      {/* 日志统计饼图 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="最近 1 小时日志统计">
            {logStats && logStats.by_level.length > 0 ? (
              <Row gutter={16} align="middle">
                <Col xs={24} md={8}>
                  <Statistic title="日志总量" value={logStats.by_level.reduce((s, l) => s + l.count, 0)} />
                  <div style={{ marginTop: 8 }}>
                    {logStats.by_level.map(({ level, count }) => (
                      <Tag key={level} color={{ DEBUG: 'default', INFO: 'blue', WARN: 'orange', ERROR: 'red', FATAL: 'purple' }[level] || 'default'} style={{ marginBottom: 4 }}>
                        {level}: {count}
                      </Tag>
                    ))}
                  </div>
                </Col>
                <Col xs={24} md={16}>
                  <ReactECharts style={{ height: 200 }} option={{
                    tooltip: { trigger: 'item' as const },
                    series: [{
                      type: 'pie' as const,
                      radius: ['40%', '70%'],
                      data: logStats.by_level.filter(l => l.count > 0).map(({ level, count }) => ({
                        name: level, value: count,
                        itemStyle: { color: { DEBUG: '#bfbfbf', INFO: '#1677ff', WARN: '#faad14', ERROR: '#ff4d4f', FATAL: '#722ed1' }[level] || '#999' },
                      })),
                      label: { formatter: '{b}: {c}' },
                    }],
                  }} />
                </Col>
              </Row>
            ) : (
              <Typography.Text type="secondary">暂无数据</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* 最新告警列表 */}
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
