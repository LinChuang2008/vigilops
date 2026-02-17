/**
 * 仪表盘页面
 *
 * 全局鸟瞰视角：
 * - 核心指标统计卡片 + 系统健康评分
 * - 服务器健康总览条（每台一个迷你卡片，点击跳转详情）
 * - 24 小时趋势迷你图（支持按服务器筛选）
 * - 多服务器资源对比（CPU/内存/磁盘横向对比）
 * - 网络带宽、日志统计、最新告警
 * 支持 WebSocket 实时推送，断线自动降级为 30 秒轮询。
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Row, Col, Card, Statistic, Typography, Tag, Table, Spin, Button,
  Dropdown, Progress, Tooltip, Space,
} from 'antd';
import {
  DownloadOutlined, CloudServerOutlined, ApiOutlined, AlertOutlined,
  CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined,
  DesktopOutlined, ArrowRightOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import api from '../services/api';
import { fetchLogStats } from '../services/logs';
import type { LogStats } from '../services/logs';
import { databaseService } from '../services/databases';
import type { DatabaseItem } from '../services/databases';

const { Title, Text } = Typography;

/* ==================== 类型定义 ==================== */

interface HostItem {
  id: string;
  hostname: string;
  ip_address?: string;
  status: string;
  cpu_cores?: number;
  memory_total_mb?: number;
  latest_metrics?: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent?: number;
    disk_used_mb?: number;
    disk_total_mb?: number;
    net_send_rate_kb?: number;
    net_recv_rate_kb?: number;
    net_packet_loss_rate?: number;
  };
}

interface DashboardData {
  hosts: { total: number; online: number; offline: number; items: HostItem[] };
  services: { total: number; healthy: number; unhealthy: number };
  alerts: {
    total: number; firing: number;
    items: Array<{ id: string; title: string; severity: string; status: string; fired_at: string }>;
  };
}

interface WsDashboardData {
  timestamp: string;
  hosts: { total: number; online: number; offline: number };
  services: { total: number; up: number; down: number };
  alerts: { total: number; firing: number };
  health_score: number;
}

interface TrendPoint {
  hour: string;
  avg_cpu: number | null;
  avg_mem: number | null;
  alert_count: number;
  error_log_count: number;
}

/* ==================== 组件 ==================== */

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [logStats, setLogStats] = useState<LogStats | null>(null);
  const [dbItems, setDbItems] = useState<DatabaseItem[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsData, setWsData] = useState<WsDashboardData | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const navigate = useNavigate();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** 获取仪表盘数据 */
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
          online: hosts.items?.filter((h: HostItem) => h.status === 'online').length || 0,
          offline: hosts.items?.filter((h: HostItem) => h.status === 'offline').length || 0,
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
      try { setLogStats(await fetchLogStats('1h')); } catch {}
      try { setDbItems((await databaseService.list()).data.databases || []); } catch {}
    } catch {} finally { setLoading(false); }
  }, []);

  const fetchTrends = useCallback(async () => {
    try { setTrends((await api.get('/dashboard/trends')).data.trends || []); } catch {}
  }, []);

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = setInterval(() => { fetchData(); fetchTrends(); }, 30000);
  }, [fetchData, fetchTrends]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) { clearInterval(pollTimerRef.current); pollTimerRef.current = null; }
  }, []);

  const connectWs = useCallback(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws/dashboard`;
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => { setWsConnected(true); stopPolling(); };
      ws.onmessage = (e) => { try { setWsData(JSON.parse(e.data)); } catch {} };
      ws.onclose = () => { setWsConnected(false); wsRef.current = null; startPolling(); reconnectTimerRef.current = setTimeout(connectWs, 5000); };
      ws.onerror = () => { ws.close(); };
    } catch { startPolling(); reconnectTimerRef.current = setTimeout(connectWs, 5000); }
  }, [startPolling, stopPolling]);

  useEffect(() => {
    fetchData(); fetchTrends(); connectWs();
    return () => {
      wsRef.current?.close();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      stopPolling();
    };
  }, [fetchData, fetchTrends, connectWs, stopPolling]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const d = data || { hosts: { total: 0, online: 0, offline: 0, items: [] }, services: { total: 0, healthy: 0, unhealthy: 0 }, alerts: { total: 0, firing: 0, items: [] } };

  const hostTotal = wsData?.hosts.total ?? d.hosts.total;
  const hostOnline = wsData?.hosts.online ?? d.hosts.online;
  const hostOffline = wsData?.hosts.offline ?? d.hosts.offline;
  const svcTotal = wsData?.services.total ?? d.services.total;
  const svcHealthy = wsData?.services.up ?? d.services.healthy;
  const svcUnhealthy = wsData?.services.down ?? d.services.unhealthy;
  const alertFiring = wsData?.alerts.firing ?? d.alerts.firing;
  const healthScore = wsData?.health_score ?? 100;
  const scoreColor = healthScore > 80 ? '#52c41a' : healthScore >= 60 ? '#faad14' : '#ff4d4f';

  /** 迷你图配置 */
  const sparklineOption = (values: (number | null)[], color: string, title: string) => ({
    title: { text: title, left: 'center', top: 0, textStyle: { fontSize: 12, color: '#666' } },
    tooltip: { trigger: 'axis' as const, formatter: (params: any) => params[0]?.value != null ? `${params[0].value}` : '无数据' },
    xAxis: { type: 'category' as const, show: false, data: values.map((_, i) => i) },
    yAxis: { type: 'value' as const, show: false },
    series: [{ type: 'line' as const, data: values, smooth: true, symbol: 'none', lineStyle: { color, width: 2 }, areaStyle: { color: `${color}33` } }],
    grid: { top: 25, bottom: 5, left: 5, right: 5 },
  });

  /** 多服务器资源对比图 */
  const resourceCompareOption = () => {
    const hosts = d.hosts.items.filter(h => h.latest_metrics);
    if (hosts.length === 0) return null;
    const names = hosts.map(h => h.hostname);
    return {
      tooltip: { trigger: 'axis' as const },
      legend: { bottom: 0, data: ['CPU', '内存', '磁盘'] },
      xAxis: { type: 'category' as const, data: names, axisLabel: { rotate: names.length > 3 ? 30 : 0, fontSize: 11 } },
      yAxis: { type: 'value' as const, max: 100, axisLabel: { formatter: '{value}%' } },
      series: [
        { name: 'CPU', type: 'bar' as const, data: hosts.map(h => h.latest_metrics!.cpu_percent ?? 0), itemStyle: { color: '#1677ff' }, barMaxWidth: 40 },
        { name: '内存', type: 'bar' as const, data: hosts.map(h => h.latest_metrics!.memory_percent ?? 0), itemStyle: { color: '#52c41a' }, barMaxWidth: 40 },
        { name: '磁盘', type: 'bar' as const, data: hosts.map(h => h.latest_metrics!.disk_percent ?? 0), itemStyle: { color: '#faad14' }, barMaxWidth: 40 },
      ],
      grid: { top: 20, bottom: 60, left: 50, right: 20 },
    };
  };

  /** 网络带宽对比图 */
  const networkCompareOption = () => {
    const hosts = d.hosts.items.filter(h => h.latest_metrics?.net_send_rate_kb != null);
    if (hosts.length === 0) return null;
    return {
      tooltip: { trigger: 'axis' as const },
      legend: { bottom: 0 },
      xAxis: { type: 'category' as const, data: hosts.map(h => h.hostname), axisLabel: { rotate: hosts.length > 3 ? 30 : 0 } },
      yAxis: { type: 'value' as const, axisLabel: { formatter: '{value} KB/s' } },
      series: [
        { name: '上传', type: 'bar' as const, data: hosts.map(h => h.latest_metrics!.net_send_rate_kb ?? 0), itemStyle: { color: '#1677ff' } },
        { name: '下载', type: 'bar' as const, data: hosts.map(h => h.latest_metrics!.net_recv_rate_kb ?? 0), itemStyle: { color: '#52c41a' } },
      ],
      grid: { top: 20, bottom: 60, left: 60, right: 20 },
    };
  };

  const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };

  /** CSV 导出 */
  const exportCSV = () => {
    const rows: any[][] = [
      ['指标', '总数', '正常', '异常'],
      ['服务器', d.hosts.total, d.hosts.online, d.hosts.offline],
      ['服务', d.services.total, d.services.healthy, d.services.unhealthy],
      ['数据库', dbItems.length, dbItems.filter(x => x.status === 'healthy').length, dbItems.filter(x => x.status !== 'healthy' && x.status !== 'unknown').length],
      ['活跃告警', d.alerts.firing, '', ''],
      [], ['服务器', 'CPU%', '内存%', '磁盘%', '上传KB/s', '下载KB/s'],
    ];
    d.hosts.items.filter(h => h.latest_metrics).forEach(h => {
      const m = h.latest_metrics!;
      rows.push([h.hostname, m.cpu_percent, m.memory_percent, m.disk_percent ?? '', m.net_send_rate_kb ?? '', m.net_recv_rate_kb ?? '']);
    });
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `dashboard_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const cpuTrend = trends.map(t => t.avg_cpu);
  const memTrend = trends.map(t => t.avg_mem);
  const alertTrend = trends.map(t => t.alert_count);
  const errorTrend = trends.map(t => t.error_log_count);

  const resOption = resourceCompareOption();
  const netOption = networkCompareOption();

  return (
    <div>
      {/* 标题栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>系统概览</Title>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#999' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: wsConnected ? '#52c41a' : '#d9d9d9', display: 'inline-block' }} />
            {wsConnected ? '实时' : '轮询'}
          </span>
        </Space>
        <Dropdown menu={{ items: [{ key: 'csv', label: '导出 CSV', onClick: exportCSV }] }}>
          <Button icon={<DownloadOutlined />}>导出数据</Button>
        </Dropdown>
      </div>

      {/* ===== 第一行：核心指标卡片 + 健康评分 ===== */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={5}>
          <Card><Statistic title="服务器" value={hostTotal} prefix={<CloudServerOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag icon={<CheckCircleOutlined />} color="success">在线 {hostOnline}</Tag>
              <Tag icon={<CloseCircleOutlined />} color="error">离线 {hostOffline}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Card><Statistic title="服务" value={svcTotal} prefix={<ApiOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {svcHealthy}</Tag>
              <Tag color="error">异常 {svcUnhealthy}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Card><Statistic title="数据库" value={dbItems.length} prefix={<DatabaseOutlined />} />
            <div style={{ marginTop: 8 }}>
              <Tag color="success">健康 {dbItems.filter(x => x.status === 'healthy').length}</Tag>
              <Tag color="error">异常 {dbItems.filter(x => x.status !== 'healthy' && x.status !== 'unknown').length}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Card>
            <Statistic title="活跃告警" value={alertFiring} prefix={<AlertOutlined />}
              valueStyle={{ color: alertFiring > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card style={{ textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 14 }}>健康评分</Text>
            <div style={{ marginTop: 8 }}>
              <Progress type="circle" percent={healthScore} size={80} strokeColor={scoreColor}
                format={(p) => <span style={{ color: scoreColor, fontWeight: 'bold' }}>{p}</span>} />
            </div>
          </Card>
        </Col>
      </Row>

      {/* ===== 第二行：服务器健康总览条 ===== */}
      {d.hosts.items.length > 0 && (
        <Card
          title={<Space><DesktopOutlined /> 服务器健康总览</Space>}
          size="small"
          style={{ marginTop: 16 }}
          styles={{ body: { padding: '12px 16px' } }}
        >
          <Row gutter={[12, 12]}>
            {d.hosts.items.map(host => {
              const m = host.latest_metrics;
              const isOnline = host.status === 'online';
              const cpuHigh = (m?.cpu_percent ?? 0) > 80;
              const memHigh = (m?.memory_percent ?? 0) > 80;
              const diskHigh = (m?.disk_percent ?? 0) > 85;
              const hasWarning = cpuHigh || memHigh || diskHigh;

              return (
                <Col key={host.id} xs={24} sm={12} md={8} lg={6}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => navigate(`/hosts/${host.id}`)}
                    style={{
                      borderLeft: `3px solid ${!isOnline ? '#ff4d4f' : hasWarning ? '#faad14' : '#52c41a'}`,
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Space size={4}>
                        <span style={{
                          width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
                          backgroundColor: isOnline ? '#52c41a' : '#ff4d4f',
                        }} />
                        <Text strong style={{ fontSize: 13 }}>{host.hostname}</Text>
                      </Space>
                      <ArrowRightOutlined style={{ color: '#999', fontSize: 11 }} />
                    </div>
                    {m ? (
                      <div style={{ display: 'flex', gap: 12 }}>
                        <Tooltip title={`CPU: ${m.cpu_percent}%`}>
                          <div style={{ flex: 1 }}>
                            <Text type="secondary" style={{ fontSize: 11 }}>CPU</Text>
                            <Progress
                              percent={m.cpu_percent}
                              size="small"
                              showInfo={false}
                              strokeColor={cpuHigh ? '#ff4d4f' : '#1677ff'}
                            />
                            <Text style={{ fontSize: 11, color: cpuHigh ? '#ff4d4f' : undefined }}>{m.cpu_percent}%</Text>
                          </div>
                        </Tooltip>
                        <Tooltip title={`内存: ${m.memory_percent}%`}>
                          <div style={{ flex: 1 }}>
                            <Text type="secondary" style={{ fontSize: 11 }}>内存</Text>
                            <Progress
                              percent={m.memory_percent}
                              size="small"
                              showInfo={false}
                              strokeColor={memHigh ? '#ff4d4f' : '#52c41a'}
                            />
                            <Text style={{ fontSize: 11, color: memHigh ? '#ff4d4f' : undefined }}>{m.memory_percent}%</Text>
                          </div>
                        </Tooltip>
                        {m.disk_percent != null && (
                          <Tooltip title={`磁盘: ${m.disk_percent}%`}>
                            <div style={{ flex: 1 }}>
                              <Text type="secondary" style={{ fontSize: 11 }}>磁盘</Text>
                              <Progress
                                percent={m.disk_percent}
                                size="small"
                                showInfo={false}
                                strokeColor={diskHigh ? '#ff4d4f' : '#faad14'}
                              />
                              <Text style={{ fontSize: 11, color: diskHigh ? '#ff4d4f' : undefined }}>{m.disk_percent}%</Text>
                            </div>
                          </Tooltip>
                        )}
                      </div>
                    ) : (
                      <Text type="secondary" style={{ fontSize: 12 }}>暂无指标数据</Text>
                    )}
                  </Card>
                </Col>
              );
            })}
          </Row>
        </Card>
      )}

      {/* ===== 第三行：24 小时趋势 ===== */}
      {trends.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(cpuTrend, '#1677ff', 'CPU 趋势 (24h)')} style={{ height: 80 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(memTrend, '#52c41a', '内存趋势 (24h)')} style={{ height: 80 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(alertTrend, '#faad14', '告警趋势 (24h)')} style={{ height: 80 }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card bodyStyle={{ padding: '12px' }}>
              <ReactECharts option={sparklineOption(errorTrend, '#ff4d4f', '错误日志 (24h)')} style={{ height: 80 }} />
            </Card>
          </Col>
        </Row>
      )}

      {/* ===== 第四行：资源对比 + 网络带宽 ===== */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="资源使用率对比">
            {resOption ? (
              <ReactECharts option={resOption} style={{ height: 260 }} />
            ) : <Text type="secondary">暂无数据</Text>}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="网络带宽 (KB/s)">
            {netOption ? (
              <ReactECharts option={netOption} style={{ height: 260 }} />
            ) : <Text type="secondary">暂无数据</Text>}
          </Card>
        </Col>
      </Row>

      {/* ===== 第五行：日志统计 ===== */}
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
                    series: [{ type: 'pie' as const, radius: ['40%', '70%'],
                      data: logStats.by_level.filter(l => l.count > 0).map(({ level, count }) => ({
                        name: level, value: count,
                        itemStyle: { color: { DEBUG: '#bfbfbf', INFO: '#1677ff', WARN: '#faad14', ERROR: '#ff4d4f', FATAL: '#722ed1' }[level] || '#999' },
                      })),
                      label: { formatter: '{b}: {c}' },
                    }],
                  }} />
                </Col>
              </Row>
            ) : <Text type="secondary">暂无数据</Text>}
          </Card>
        </Col>
      </Row>

      {/* ===== 第六行：最新告警 ===== */}
      <Card title="最新告警" style={{ marginTop: 16 }}>
        <Table
          dataSource={d.alerts.items}
          rowKey="id"
          pagination={false}
          size="small"
          columns={[
            { title: '标题', dataIndex: 'title', key: 'title' },
            { title: '严重级别', dataIndex: 'severity', key: 'severity',
              render: (s: string) => <Tag color={severityColor[s] || 'default'}>{s}</Tag> },
            { title: '触发时间', dataIndex: 'fired_at', key: 'fired_at',
              render: (t: string) => new Date(t).toLocaleString() },
          ]}
          locale={{ emptyText: '暂无活跃告警' }}
        />
      </Card>
    </div>
  );
}
