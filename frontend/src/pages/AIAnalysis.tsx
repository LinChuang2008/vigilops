/**
 * AI 智能分析页面
 *
 * 包含三大功能区域：
 * 1. 系统概况卡片 - 展示主机、服务、告警、错误日志数量及平均 CPU/内存使用率
 * 2. AI 对话 - 用户可通过自然语言向 AI 提问系统运行状况
 * 3. AI 洞察列表 - 展示 AI 自动分析产生的异常检测、根因分析等结果
 */
import { useEffect, useState, useRef } from 'react';
import { Row, Col, Card, Statistic, Typography, Tag, Table, Button, Input, Space, Select, Progress, Collapse, Spin, message } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
  AlertOutlined,
  FileTextOutlined,
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../services/api';

const { Title, Text, Paragraph } = Typography;

/** 后端返回的系统概况原始数据结构 */
interface SystemSummaryRaw {
  hosts: { total: number; online: number; offline: number };
  services: { total: number; up: number; down: number };
  /** 最近 1 小时的告警和错误日志数 */
  recent_1h: { alert_count: number; error_log_count: number };
  /** 平均资源使用率 */
  avg_usage: { cpu_percent: number; memory_percent: number };
}

/** 前端使用的系统概况（扁平化结构） */
interface SystemSummary {
  total_hosts: number;
  online_hosts: number;
  offline_hosts: number;
  total_services: number;
  healthy_services: number;
  unhealthy_services: number;
  /** 最近 1 小时告警数 */
  alerts_1h: number;
  /** 最近 1 小时错误日志数 */
  error_logs_1h: number;
  /** 平均 CPU 使用率 */
  avg_cpu: number;
  /** 平均内存使用率 */
  avg_memory: number;
}

/** 聊天消息结构 */
interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  /** AI 回答的参考来源 */
  sources?: Array<{ type: string; summary: string }>;
}

/** AI 洞察条目 */
interface InsightItem {
  id: number;
  /** 洞察类型：anomaly/root_cause/chat/trend */
  insight_type: string;
  /** 严重级别 */
  severity: string;
  title: string;
  summary: string;
  /** 详情数据（结构不固定） */
  details: any;
  /** 关联的主机 ID */
  related_host_id: number | null;
  /** 状态：new/acknowledged/resolved */
  status: string;
  created_at: string;
}

/** 严重级别颜色映射 */
const severityColor: Record<string, string> = { critical: 'red', high: 'orange', warning: 'gold', medium: 'orange', low: 'blue', info: 'blue' };
/** 洞察类型中文标签映射 */
const insightTypeLabel: Record<string, string> = { anomaly: '异常检测', root_cause: '根因分析', chat: '对话', trend: '趋势' };

/** 快捷提问列表 */
const quickQuestions = ['系统健康状况如何？', '最近有什么异常？', '性能趋势分析'];

/**
 * AI 智能分析页面组件
 */
export default function AIAnalysis() {
  // ========== 系统概况 ==========
  const [summary, setSummary] = useState<SystemSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  // ========== AI 对话 ==========
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  /** 聊天区域底部锚点，用于自动滚动 */
  const chatEndRef = useRef<HTMLDivElement>(null);

  // ========== AI 洞察列表 ==========
  const [insights, setInsights] = useState<InsightItem[]>([]);
  const [insightsTotal, setInsightsTotal] = useState(0);
  const [insightsLoading, setInsightsLoading] = useState(true);
  const [insightsPage, setInsightsPage] = useState(1);
  /** 洞察严重级别筛选 */
  const [insightSeverity, setInsightSeverity] = useState<string>('');
  /** 洞察状态筛选 */
  const [insightStatus, setInsightStatus] = useState<string>('');
  /** 手动触发分析的加载状态 */
  const [analyzeLoading, setAnalyzeLoading] = useState(false);

  const [messageApi, contextHolder] = message.useMessage();

  /** 获取系统概况数据，将后端原始结构转为扁平化格式 */
  const fetchSummary = async () => {
    setSummaryLoading(true);
    try {
      const { data } = await api.get<SystemSummaryRaw>('/ai/system-summary');
      setSummary({
        total_hosts: data.hosts?.total ?? 0,
        online_hosts: data.hosts?.online ?? 0,
        offline_hosts: data.hosts?.offline ?? 0,
        total_services: data.services?.total ?? 0,
        healthy_services: data.services?.up ?? 0,
        unhealthy_services: data.services?.down ?? 0,
        alerts_1h: data.recent_1h?.alert_count ?? 0,
        error_logs_1h: data.recent_1h?.error_log_count ?? 0,
        avg_cpu: data.avg_usage?.cpu_percent ?? 0,
        avg_memory: data.avg_usage?.memory_percent ?? 0,
      });
    } catch { /* ignore */ } finally { setSummaryLoading(false); }
  };

  /** 获取 AI 洞察列表，支持按严重级别和状态筛选 */
  const fetchInsights = async () => {
    setInsightsLoading(true);
    try {
      const params: Record<string, unknown> = { page: insightsPage, page_size: 10 };
      if (insightSeverity) params.severity = insightSeverity;
      if (insightStatus) params.status = insightStatus;
      const { data } = await api.get('/ai/insights', { params });
      setInsights(data.items || []);
      setInsightsTotal(data.total || 0);
    } catch { /* ignore */ } finally { setInsightsLoading(false); }
  };

  useEffect(() => { fetchSummary(); }, []);
  useEffect(() => { fetchInsights(); }, [insightsPage, insightSeverity, insightStatus]);

  // 聊天消息更新时自动滚动到底部
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /** 发送聊天消息：追加用户消息，调用 AI 接口，追加 AI 回复 */
  const sendChat = async (question: string) => {
    if (!question.trim()) return;
    const q = question.trim();
    setChatInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setChatLoading(true);
    try {
      const { data } = await api.post('/ai/chat', { question: q });
      setMessages(prev => [...prev, { role: 'ai', content: data.answer, sources: data.sources }]);
    } catch {
      setMessages(prev => [...prev, { role: 'ai', content: '抱歉，AI 分析暂时不可用，请稍后再试。' }]);
    } finally { setChatLoading(false); }
  };

  /** 手动触发日志分析，完成后刷新洞察列表 */
  const handleAnalyze = async () => {
    setAnalyzeLoading(true);
    try {
      await api.post('/ai/analyze-logs', { hours: 1 });
      messageApi.success('分析完成');
      fetchInsights();
    } catch {
      messageApi.error('分析失败');
    } finally { setAnalyzeLoading(false); }
  };

  /** 洞察列表表格列定义 */
  const insightColumns = [
    {
      title: '时间', dataIndex: 'created_at', width: 170,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '类型', dataIndex: 'insight_type', width: 100,
      render: (t: string) => <Tag>{insightTypeLabel[t] || t}</Tag>,
    },
    {
      title: '严重性', dataIndex: 'severity', width: 90,
      render: (s: string) => <Tag color={severityColor[s] || 'default'}>{s}</Tag>,
    },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (s: string) => <Tag color={s === 'resolved' ? 'green' : s === 'new' ? 'blue' : 'default'}>{s}</Tag>,
    },
  ];

  return (
    <div>
      {contextHolder}
      <Title level={4}><RobotOutlined /> AI 智能分析</Title>

      {/* 系统概况统计卡片 */}
      <Spin spinning={summaryLoading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic title="主机" value={summary?.online_hosts ?? '-'} suffix={`/ ${summary?.total_hosts ?? '-'}`} prefix={<CloudServerOutlined />} />
              <Text type="secondary">在线 / 总数</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic title="服务" value={summary?.healthy_services ?? '-'} suffix={`/ ${summary?.total_services ?? '-'}`} prefix={<ApiOutlined />} />
              <Text type="secondary">健康 / 总数</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic title="1h 告警" value={summary?.alerts_1h ?? '-'} prefix={<AlertOutlined />}
                valueStyle={{ color: (summary?.alerts_1h ?? 0) > 0 ? '#cf1322' : '#3f8600' }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic title="1h 错误日志" value={summary?.error_logs_1h ?? '-'} prefix={<FileTextOutlined />}
                valueStyle={{ color: (summary?.error_logs_1h ?? 0) > 0 ? '#cf1322' : '#3f8600' }} />
            </Card>
          </Col>
        </Row>
        {/* 平均 CPU / 内存使用率环形进度条 */}
        {summary && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} sm={6}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Progress type="circle" percent={Math.round(summary.avg_cpu)} size={80}
                  strokeColor={summary.avg_cpu > 80 ? '#ff4d4f' : summary.avg_cpu > 60 ? '#faad14' : '#52c41a'} />
                <div style={{ marginTop: 8 }}><Text type="secondary">平均 CPU</Text></div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Progress type="circle" percent={Math.round(summary.avg_memory)} size={80}
                  strokeColor={summary.avg_memory > 80 ? '#ff4d4f' : summary.avg_memory > 60 ? '#faad14' : '#52c41a'} />
                <div style={{ marginTop: 8 }}><Text type="secondary">平均内存</Text></div>
              </Card>
            </Col>
          </Row>
        )}
      </Spin>

      {/* AI 对话区域 */}
      <Card title={<><RobotOutlined /> AI 对话</>} style={{ marginTop: 16 }}>
        {/* 消息展示区 */}
        <div style={{
          background: '#f5f7fa', borderRadius: 8, padding: 16, minHeight: 200, maxHeight: 400, overflowY: 'auto', marginBottom: 16,
        }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              <RobotOutlined style={{ fontSize: 40, marginBottom: 12 }} />
              <div>向 AI 提问，了解系统运行状况</div>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 12,
            }}>
              <div style={{
                maxWidth: '70%',
                padding: '10px 14px',
                borderRadius: 12,
                background: msg.role === 'user' ? '#1677ff' : '#fff',
                color: msg.role === 'user' ? '#fff' : '#333',
                border: msg.role === 'ai' ? '1px solid #e8e8e8' : 'none',
                boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
              }}>
                <div style={{ marginBottom: 4 }}>
                  {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  <Text style={{ marginLeft: 6, color: msg.role === 'user' ? '#fff' : '#666', fontSize: 12 }}>
                    {msg.role === 'user' ? '你' : 'AI 助手'}
                  </Text>
                </div>
                <Paragraph style={{ margin: 0, color: msg.role === 'user' ? '#fff' : '#333', whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </Paragraph>
                {/* AI 回答的参考来源折叠面板 */}
                {msg.sources && msg.sources.length > 0 && (
                  <Collapse ghost style={{ marginTop: 8 }} items={[{
                    key: '1',
                    label: <Text type="secondary" style={{ fontSize: 12 }}>参考来源 ({msg.sources.length})</Text>,
                    children: msg.sources.map((s, j) => (
                      <div key={j} style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                        <Tag>{s.type}</Tag> {s.summary}
                      </div>
                    )),
                  }]} />
                )}
              </div>
            </div>
          ))}
          {/* AI 思考中加载提示 */}
          {chatLoading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
              <div style={{ padding: '10px 14px', borderRadius: 12, background: '#fff', border: '1px solid #e8e8e8' }}>
                <Spin size="small" /> <Text type="secondary">AI 正在思考...</Text>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        {/* 快捷提问按钮 */}
        <Space wrap style={{ marginBottom: 12 }}>
          {quickQuestions.map(q => (
            <Button key={q} size="small" icon={<ThunderboltOutlined />} onClick={() => sendChat(q)} disabled={chatLoading}>
              {q}
            </Button>
          ))}
        </Space>
        {/* 输入框 */}
        <Input.Search
          placeholder="输入问题，例如：最近有没有异常？"
          enterButton={<><SendOutlined /> 发送</>}
          value={chatInput}
          onChange={e => setChatInput(e.target.value)}
          onSearch={sendChat}
          loading={chatLoading}
          size="large"
        />
      </Card>

      {/* AI 洞察列表 */}
      <Card title="AI 洞察列表" style={{ marginTop: 16 }}
        extra={
          <Button type="primary" icon={<ThunderboltOutlined />} loading={analyzeLoading} onClick={handleAnalyze}>
            手动触发分析
          </Button>
        }
      >
        {/* 筛选条件 */}
        <Row style={{ marginBottom: 16 }}>
          <Space>
            <Select placeholder="严重性" allowClear style={{ width: 120 }}
              onChange={v => { setInsightSeverity(v || ''); setInsightsPage(1); }}
              options={[
                { label: 'Critical', value: 'critical' },
                { label: 'High', value: 'high' },
                { label: 'Medium', value: 'medium' },
                { label: 'Low', value: 'low' },
                { label: 'Info', value: 'info' },
              ]}
            />
            <Select placeholder="状态" allowClear style={{ width: 120 }}
              onChange={v => { setInsightStatus(v || ''); setInsightsPage(1); }}
              options={[
                { label: '新建', value: 'new' },
                { label: '已确认', value: 'acknowledged' },
                { label: '已解决', value: 'resolved' },
              ]}
            />
          </Space>
        </Row>
        <Table
          dataSource={insights}
          columns={insightColumns}
          rowKey="id"
          loading={insightsLoading}
          pagination={{ current: insightsPage, pageSize: 10, total: insightsTotal, onChange: p => setInsightsPage(p) }}
          expandable={{
            expandedRowRender: (record: InsightItem) => (
              <div style={{ padding: '8px 0' }}>
                <Paragraph><strong>摘要：</strong>{record.summary}</Paragraph>
                {record.details && (
                  <Paragraph>
                    <strong>详情：</strong>
                    <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, fontSize: 12, maxHeight: 300, overflow: 'auto' }}>
                      {typeof record.details === 'string' ? record.details : JSON.stringify(record.details, null, 2)}
                    </pre>
                  </Paragraph>
                )}
              </div>
            ),
          }}
        />
      </Card>
    </div>
  );
}
