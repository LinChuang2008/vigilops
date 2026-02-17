/**
 * 数据库详情页面
 * 展示单个数据库的基本信息和性能监控图表，包括连接数趋势、数据库大小、
 * 慢查询、事务统计等。Oracle 数据库额外展示表空间使用率和慢查询 Top 10。
 * 支持时间范围切换，每 30 秒自动刷新。
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Descriptions, Tag, Spin, Typography, Select, Space, Table } from 'antd';
import ReactECharts from 'echarts-for-react';
import { databaseService } from '../services/databases';
import type { DatabaseItem, DatabaseMetric, SlowQuery } from '../services/databases';

/** 状态对应的 Tag 颜色映射 */
const statusColor: Record<string, string> = { healthy: 'success', warning: 'warning', critical: 'error', unknown: 'default' };

/**
 * 数据库详情组件
 * 通过路由参数 id 获取数据库信息、历史指标和慢查询数据
 */
export default function DatabaseDetail() {
  const { id } = useParams<{ id: string }>();
  const [db, setDb] = useState<DatabaseItem | null>(null);
  const [metrics, setMetrics] = useState<DatabaseMetric[]>([]);
  /** Oracle 慢查询列表 */
  const [slowQueries, setSlowQueries] = useState<SlowQuery[]>([]);
  const [loading, setLoading] = useState(true);
  /** 时间范围选择：1h / 6h / 24h / 7d */
  const [timeRange, setTimeRange] = useState('1h');

  /** 获取数据库基本信息和指标数据，Oracle 额外获取慢查询 */
  const fetchData = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [dbRes, metricsRes] = await Promise.all([
        databaseService.get(id),
        databaseService.getMetrics(id, timeRange),
      ]);
      setDb(dbRes.data);
      setMetrics(metricsRes.data.metrics || []);
      // Oracle 数据库额外获取慢查询
      if (dbRes.data.db_type === 'oracle') {
        try {
          const sqRes = await databaseService.getSlowQueries(id);
          setSlowQueries(sqRes.data.slow_queries || []);
        } catch { /* ignore */ }
      }
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [id, timeRange]);

  // 每 30 秒自动刷新指标数据
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [id, timeRange]);

  // Oracle 慢查询每 60 秒单独刷新
  useEffect(() => {
    if (!id || !db || db.db_type !== 'oracle') return;
    const interval = setInterval(async () => {
      try {
        const sqRes = await databaseService.getSlowQueries(id);
        setSlowQueries(sqRes.data.slow_queries || []);
      } catch { /* ignore */ }
    }, 60000);
    return () => clearInterval(interval);
  }, [id, db?.db_type]);

  if (loading && !db) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!db) return <Typography.Text>数据库不存在</Typography.Text>;

  // 提取时间轴标签
  const timestamps = metrics.map(m => m.recorded_at ? new Date(m.recorded_at).toLocaleTimeString() : '');

  /**
   * 生成折线图通用配置
   * @param title 图表标题
   * @param series 数据系列
   * @param yFormatter Y 轴格式化字符串
   */
  const lineOption = (title: string, series: { name: string; data: (number | null)[]; color: string }[], yFormatter = '{value}') => ({
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' as const },
    legend: { bottom: 0 },
    xAxis: { type: 'category' as const, data: timestamps, axisLabel: { rotate: 30 } },
    yAxis: { type: 'value' as const, axisLabel: { formatter: yFormatter } },
    series: series.map(s => ({ ...s, type: 'line' as const, smooth: true, areaStyle: { opacity: 0.1 } })),
    grid: { top: 40, bottom: 60, left: 60, right: 20 },
  });

  // 数据库类型显示名称
  const dbTypeName = db.db_type === 'postgres' || db.db_type === 'postgresql' ? 'PostgreSQL' : db.db_type === 'mysql' ? 'MySQL' : db.db_type === 'oracle' ? 'Oracle' : db.db_type;
  const isOracle = db.db_type === 'oracle';

  /** Oracle 慢查询表格列定义 */
  const slowQueryColumns = [
    { title: 'SQL ID', dataIndex: 'sql_id', key: 'sql_id', width: 140 },
    { title: '平均耗时(秒)', dataIndex: 'avg_seconds', key: 'avg_seconds', width: 120, render: (v: number) => v?.toFixed(2) },
    { title: '执行次数', dataIndex: 'executions', key: 'executions', width: 100 },
    { title: 'SQL 文本', dataIndex: 'sql_text', key: 'sql_text', ellipsis: true },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Typography.Title level={4} style={{ margin: 0 }}>{db.name}</Typography.Title></Col>
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

      {/* 数据库基本信息卡片 */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 4 }}>
          <Descriptions.Item label="数据库名">{db.name}</Descriptions.Item>
          <Descriptions.Item label="类型">{dbTypeName}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColor[db.status] || 'default'}>{db.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="更新时间">{db.updated_at ? new Date(db.updated_at).toLocaleString() : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 监控图表网格 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('连接数趋势', [
              { name: '总连接', data: metrics.map(m => m.connections_total), color: '#1677ff' },
              { name: '活跃连接', data: metrics.map(m => m.connections_active), color: '#52c41a' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('数据库大小趋势', [
              { name: '大小 (MB)', data: metrics.map(m => m.database_size_mb), color: '#faad14' },
            ], '{value} MB')} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('慢查询趋势', [
              { name: '慢查询', data: metrics.map(m => m.slow_queries), color: '#ff4d4f' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card>
            <ReactECharts option={lineOption('事务趋势', [
              { name: '已提交', data: metrics.map(m => m.transactions_committed), color: '#1677ff' },
              { name: '已回滚', data: metrics.map(m => m.transactions_rolled_back), color: '#ff4d4f' },
            ])} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      {/* Oracle 专属：表空间使用率和慢查询 Top 10 */}
      {isOracle && (
        <>
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} md={12}>
              <Card>
                <ReactECharts option={lineOption('表空间使用率趋势', [
                  { name: '使用率 (%)', data: metrics.map(m => m.tablespace_used_pct), color: '#722ed1' },
                ], '{value}%')} style={{ height: 280 }} />
              </Card>
            </Col>
          </Row>
          <Card title="慢查询 Top 10" style={{ marginTop: 16 }}>
            <Table
              dataSource={slowQueries}
              columns={slowQueryColumns}
              rowKey="sql_id"
              size="small"
              pagination={false}
            />
          </Card>
        </>
      )}
    </div>
  );
}
