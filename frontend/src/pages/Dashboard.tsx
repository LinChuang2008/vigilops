/**
 * 仪表盘页面
 *
 * 系统总览页，展示服务器、服务、数据库、告警等核心指标统计卡片，
 * 系统健康评分，24小时趋势迷你图，以及 CPU/内存使用率、网络带宽、
 * 丢包率的柱状图，日志级别分布饼图和最新告警列表。
 * 支持 WebSocket 实时推送，断线自动降级为 30 秒轮询。
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { Row, Col, Card, Statistic, Typography, Tag, Table, Spin, Button, Dropdown, Progress } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
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

const { Title, Text } = Typography;

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

/** WebSocket 推送的数据结构 */
interface WsDashboardData {
  timestamp: string;
  hosts: { total: number; online: number; offline: number };
  services: { total: number; up: number; down: number };
  alerts: { total: number; firing: number };
  recent_1h: { alert_count: number; error_log_count: number };
  avg_usage: { cpu_percent: number | null; memory_percent: number | null; disk_percent: number | null };
  health_score: number;
}

/** 趋势数据点 */
interface TrendPoint {
  hour: string;
  avg_cpu: number | null;
  avg_mem: number | null;
  alert_count: number;
  error_log_count: number;
}

/**
 * 仪表盘页面组件
 *
 * 页面加载时并行请求服务器、服务、告警数据，并通过 WebSocket 实时刷新。
 * WebSocket 断开时自动降级为 30 秒轮询。
 */
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  /** 日志统计数据（按级别分布） */
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  /** 数据库列表 */
  const [dbItems, setDbItems] = useState<DatabaseItem[]>([]);
  /** WebSocket 连接状态 */
  const [wsConnected, setWsConnected] = useState(false);
  /** WebSocket 推送的实时数据 */
  const [wsData, setWsData] = useState<WsDashboardData | null>(null);
  /** 趋势数据 */
  const [trends, setTrends] = useState<TrendPoint[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** 获取完整仪表盘数据（REST API） */
  const fetchData = useCallback(async () => {
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
  }, []);

  /** 获取趋势数据 */
  const fetchTrends = useCallback(async () => {
    try {
      const res = await api.get('/dashboard/trends');
      setTrends(res.data.trends || []);
    } catch { /* ignore */ }
  }, []);

  /** 启动轮询（WebSocket 断开时的降级方案） */
  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = setInterval(() => {
      fetchData();
      fetchTrends();
    }, 30000);
  }, [fetchData, fetchTrends]);

  /** 停止轮询 */
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  /** 建立 WebSocket 连接 */
  const connectWs = useCallback(() => {
    // 根据当前页面协议和地址构建 WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.hostname;
    const wsUrl = `${wsProtocol}//${wsHost}:8001/api/v1/ws/dashboard`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        // WebSocket 连接成功，停止轮询
        stopPolling();
      };

      ws.onmessage = (event) => {
        try {
          const parsed: WsDashboardData = JSON.parse(event.data);
          setWsData(parsed);
        } catch { /* 忽略解析错误 */ }
      };

      ws.onclose = () => {
        setWsConnected(false);
        wsRef.current = null;
        // 断开后启动轮询降级
        startPolling();
        // 5 秒后尝试重连
        reconnectTimerRef.current = setTimeout(connectWs, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket 创建失败，降级到轮询
      startPolling();
      reconnectTimerRef.current = setTimeout(connectWs, 5000);
    }
  }, [startPolling, stopPolling]);

  useEffect(() => {
    // 首次加载数据
    fetchData();
    fetchTrends();
    // 尝试建立 WebSocket 连接
    connectWs();

    return () => {
      // 清理 WebSocket 和定时器
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      stopPolling();
    };
  }, [fetchData, fetchTrends, connectWs, stopPolling]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  /** 数据兜底：确保即使接口未返回数据也不会报错 */
  const d = data || { hosts: { total: 0, online: 0, offline: 0, items: [] }, services: { total: 0, healthy: 0, unhealthy: 0 }, alerts: { total: 0, firing: 0, items: [] } };

  // 如果有 WebSocket 推送的数据，用它更新统计卡片
  const hostTotal = wsData?.hosts.total ?? d.hosts.total;
  const hostOnline = wsData?.hosts.online ?? d.hosts.online;
  const hostOffline = wsData?.hosts.offline ?? d.hosts.offline;
  const svcTotal = wsData?.services.total ?? d.services.total;
  const svcHealthy = wsData?.services.up ?? d.services.healthy;
  const svcUnhealthy = wsData?.services.down ?? d.services.unhealthy;
  const alertFiring = wsData?.alerts.firing ?? d.alerts.firing;
  const healthScore = wsData?.health_score ?? 100;

  /** 健康评分颜色 */
  const scoreColor = healthScore > 80 ? '#52c41a' : healthScore >= 60 ? '#faad14' : '#ff4d4f';

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

  /** 生成迷你图（sparkline）配置 */
  const sparklineOption = (
    data: (number | null)[],
    color: string,
    title: string,
  ) => ({
    title: { text: title, left: 'center', top: 0, textStyle: { fontSize: 12, color: '#666' } },
    tooltip: { trigger: 'axis' as const, formatter: (params: any) => {
      const p = params[0];
      return p?.value != null ? `${p.value}` : '无数据';
    }},
    xAxis: { type: 'category' as const, show: false, data: data.map((_, i) => i) },
    yAxis: { type: 'value' as const, show: false },
    series: [{
      type: 'line' as const,
      data,
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: { color: `${color}33` },
    }],
    grid: { top: 25, bottom: 5, left: 5, right: 5 },
  });

  /** 告警严重级别对应颜色映射 */
  const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };

  /** 导出 Dashboard 数据为 CSV 文件 */
  const exportCSV = () => {
    const rows = [
      ['指标', '总数', '正常', '异常'],
      ['服务器', d.hosts.total, d.hosts.online, d.hosts.offline],
      ['服务', d.services.total, d.services.healthy, d.services.unhealthy],
      ['数据库', dbItems.length, dbItems.filter(x => x.status === 'healthy').length, dbItems.filter(x => x.status !== 'healthy' && x.status !== 'unknown').length],
      ['活跃告警', d.alerts.firing, '', ''],
    ];
    // 添加资源使用率
    rows.push([], ['服务器', 'CPU%', '内存%']);
    d.hosts.items.filter(h => h.latest_metrics).forEach(h => {
      rows.push([h.hostname, h.latest_metrics!.cpu_percent, h.latest_metrics!.memory_percent] as any);
    });
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dashboard_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 提取趋势数据用于迷你图
  const cpuTrend = trends.map(t => t.avg_cpu);
  const memTrend = trends.map(t => t.avg_mem);
  const alertTrend = trends.map(t => t.alert_count);
  const errorTrend = trends.map(t => t.error_log_count);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Title level={4} style={{ margin: 0 }}>系统概览</Title>
          {/* WebSocket 连接状态指示器 */}
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#999' }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: wsConnected ? '#52c41a' : '#d9d9d9',
              display: 'inline-block',
            }} />
            {wsConnected ? '实时' : '离线'}
          </span>
        </div>
        <Dropdown menu={{ items: [{ key: 'csv', label: '导出 CSV', onClick: exportCSV }] }}>
          <Button icon={<DownloadOutlined />}>导出数据</Button>
        </Dropdown>
      </div>

      {/* 核心指标统计卡片 + 健康评分 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={5}>
          <Card>
            <Statistic title="服务器总数" value={hostTotal} prefix={<CloudServerOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag icon={<CheckCircleOutlined />} color="success">在线 {hostOnline}</Tag>
              <Tag icon={<CloseCircleOutlined />} color="error">离线 {hostOffline}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Card>
            <Statistic title="服务总数" value={svcTotal} prefix={<ApiOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {svcHealthy}</Tag>
              <Tag color="error">异常 {svcUnhealthy}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Card>
            <Statistic title="数据库" value={dbItems.length} prefix={<DatabaseOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {dbItems.filter(d => d.status === 'healthy').length}</Tag>
              <Tag color="error">异常 {dbItems.filter(d => d.status !== 'healthy' && d.status !== 'unknown').length}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Card>
            <Statistic title="活跃告警" value={alertFiring} prefix={<AlertOutlined />} valueStyle={{ color: alertFiring > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        {/* 系统健康评分卡片 */}
        <Col xs={24} sm={12} md={4}>
          <Card style={{ textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 14 }}>健康评分</Text>
            <div style={{ marginTop: 8 }}>
              <Progress
                type="circle"
                percent={healthScore}
                size={80}
                strokeColor={scoreColor}
                format={(percent) => <span style={{ color: scoreColor, fontWeight: 'bold' }}>{percent}</span>}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 24 小时趋势迷你图 */}
      {trends.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(cpuTrend, '#1677ff', 'CPU 趋势')} style={{ height: 80 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(memTrend, '#52c41a', '内存趋势')} style={{ height: 80 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(alertTrend, '#faad14', '告警趋势')} style={{ height: 80 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(errorTrend, '#ff4d4f', '错误日志趋势')} style={{ height: 80 }} />
            </Card>
          </Col>
        </Row>
      )}

      {/* CPU / 内存使用率图表 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="CPU 使用率">
            {cpuData.length > 0 ? (
              <ReactECharts option={barOption('', cpuData, '#1677ff')} style={{ height: 250 }} />
            ) : (
              <Text type="secondary">暂无数据</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="内存使用率">
            {memData.length > 0 ? (
              <ReactECharts option={barOption('', memData, '#52c41a')} style={{ height: 250 }} />
            ) : (
              <Text type="secondary">暂无数据</Text>
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
              if (netHosts.length === 0) return <Text type="secondary">暂无数据</Text>;
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
              if (netHosts.length === 0) return <Text type="secondary">暂无数据</Text>;
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
              <Text type="secondary">暂无数据</Text>
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
