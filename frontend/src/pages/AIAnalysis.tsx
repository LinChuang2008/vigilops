/**
 * AI 智能分析页面
 *
 * 包含三大功能区域：
 * 1. 系统概况卡片 - 展示主机、服务、告警、错误日志数量及平均 CPU/内存使用率
 * 2. AI 对话 - 用户可通过自然语言向 AI 提问系统运行状况
 * 3. AI 洞察列表 - 展示 AI 自动分析产生的异常检测、根因分析等结果
 */
import { useEffect, useState, useRef } from 'react';
import { Row, Col, Card, Statistic, Typography, Tag, Table, Button, Input, Space, Select, Progress, Collapse, Spin, message, Tooltip, Rate } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
  AlertOutlined,
  FileTextOutlined,
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../services/api';
import { aiFeedbackService } from '../services/aiFeedback';

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
  id: string; // 消息唯一ID
  role: 'user' | 'ai';
  content: string;
  /** AI 回答的参考来源 */
  sources?: Array<{ type: string; summary: string }>;
  /** 引用的历史运维记忆 */
  memory_context?: Array<Record<string, any>>;
  timestamp: number; // 消息时间戳
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

  // ========== AI 反馈 ==========
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [messageFeedback, setMessageFeedback] = useState<Record<string, { rating?: number; helpful?: boolean }>>({}); // 消息反馈状态
  
  /** 快速反馈处理（👍👎） */
  const handleQuickFeedback = async (messageId: string, message: ChatMessage, isHelpful: boolean) => {
    if (message.role !== 'ai') return;
    
    setFeedbackLoading(true);
    try {
      await aiFeedbackService.quickFeedback({
        ai_response: message.content,
        rating: isHelpful ? 4 : 2, // 👍=4分，👎=2分
        is_helpful: isHelpful
      });
      
      // 更新本地反馈状态
      setMessageFeedback(prev => ({
        ...prev,
        [messageId]: { helpful: isHelpful }
      }));
      
      messageApi.success('反馈已提交，谢谢！');
    } catch (error) {
      messageApi.error('反馈提交失败，请稍后重试');
    } finally {
      setFeedbackLoading(false);
    }
  };

  /** 评分反馈处理（1-5星） */
  const handleRatingFeedback = async (messageId: string, message: ChatMessage, rating: number) => {
    if (message.role !== 'ai' || rating === 0) return;
    
    setFeedbackLoading(true);
    try {
      await aiFeedbackService.quickFeedback({
        ai_response: message.content,
        rating: rating,
        is_helpful: rating >= 3 // 3星及以上认为有用
      });
      
      // 更新本地反馈状态
      setMessageFeedback(prev => ({
        ...prev,
        [messageId]: { rating: rating, helpful: rating >= 3 }
      }));
      
      messageApi.success('评分已提交，谢谢！');
    } catch (error) {
      messageApi.error('评分提交失败，请稍后重试');
    } finally {
      setFeedbackLoading(false);
    }
  };
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

  /** 获取系统概况数据 (Fetch system overview data)
   * 从后端获取原始嵌套结构数据，转换为前端使用的扁平化格式
   * 包含主机、服务、告警、日志统计以及平均资源使用率
   */
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

  /** 获取 AI 洞察分析列表 (Fetch AI insights analysis list)
   * 支持按严重级别(critical/high/warning/info)和状态(new/acknowledged/resolved)筛选
   * 分页显示AI自动产生的异常检测、根因分析、趋势分析等洞察
   */
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

  /** AI 对话流程处理 (AI chat flow handler)
   * 1. 追加用户消息到对话历史
   * 2. 调用后端 AI 聊天接口，传入用户问题
   * 3. 获取 AI 回答，包含答案内容、参考来源、运维记忆上下文
   * 4. 追加 AI 回复到对话历史，失败时显示友好错误信息
   */
  const sendChat = async (question: string) => {
    if (!question.trim()) return;
    const q = question.trim();
    setChatInput('');
    const userMessage: ChatMessage = {
      id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      role: 'user',
      content: q,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMessage]);
    setChatLoading(true);
    try {
      const { data } = await api.post('/ai/chat', { question: q });
      const aiMessage: ChatMessage = {
        id: `ai_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        role: 'ai',
        content: data.answer,
        sources: data.sources,
        memory_context: data.memory_context,
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch {
      const errorMessage: ChatMessage = {
        id: `ai_error_${Date.now()}`,
        role: 'ai',
        content: '抱歉，AI 分析暂时不可用，请稍后再试。',
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally { setChatLoading(false); }
  };

  /** 手动触发日志智能分析 (Manually trigger log intelligent analysis)
   * 调用 AI 引擎分析最近1小时的日志数据，识别异常模式和潜在问题
   * 分析完成后自动刷新洞察列表，展示新发现的问题
   */
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
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#999' }}>
              <RobotOutlined style={{ fontSize: 40, marginBottom: 12 }} />
              <div style={{ marginBottom: 20 }}>向 AI 提问，了解系统运行状况</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                {[
                  '试试问：系统健康状况如何？',
                  '试试问：最近有什么异常？',
                  '试试问：服务器 CPU 为何飙升？',
                ].map(hint => (
                  <Button
                    key={hint}
                    size="small"
                    type="dashed"
                    icon={<ThunderboltOutlined />}
                    onClick={() => sendChat(hint.replace(/^试试问：/, ''))}
                    style={{ color: '#595959', borderColor: '#d9d9d9' }}
                  >
                    {hint}
                  </Button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} style={{
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
                {/* 历史运维记忆引用 */}
                {msg.memory_context && msg.memory_context.length > 0 && (
                  <Collapse ghost style={{ marginTop: 4 }} items={[{
                    key: 'memory',
                    label: <Text type="secondary" style={{ fontSize: 12 }}>📚 参考了 {msg.memory_context.length} 条历史运维经验</Text>,
                    children: msg.memory_context.map((mem, j) => (
                      <div key={j} style={{ fontSize: 12, color: '#666', marginBottom: 4, padding: '4px 8px', background: '#f9f9f9', borderRadius: 4 }}>
                        {mem.content || mem.text || JSON.stringify(mem)}
                      </div>
                    )),
                  }]} />
                )}
                
                {/* AI 反馈组件 - 只在AI回答中显示 */}
                {msg.role === 'ai' && !msg.content.includes('抱歉，AI 分析暂时不可用') && (
                  <div style={{ 
                    marginTop: 8, 
                    paddingTop: 8, 
                    borderTop: '1px solid #f0f0f0',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: 12
                  }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>这个回答对你有帮助吗？</Text>
                    <Space size="small">
                      <Tooltip title="有用">
                        <Button 
                          size="small" 
                          type={messageFeedback[msg.id]?.helpful === true ? 'primary' : 'text'}
                          icon={<LikeOutlined />}
                          onClick={() => handleQuickFeedback(msg.id, msg, true)}
                          loading={feedbackLoading}
                          disabled={messageFeedback[msg.id]?.helpful !== undefined}
                        >
                          有用
                        </Button>
                      </Tooltip>
                      <Tooltip title="无用">
                        <Button 
                          size="small"
                          type={messageFeedback[msg.id]?.helpful === false ? 'primary' : 'text'} 
                          icon={<DislikeOutlined />}
                          onClick={() => handleQuickFeedback(msg.id, msg, false)}
                          loading={feedbackLoading}
                          disabled={messageFeedback[msg.id]?.helpful !== undefined}
                        >
                          无用
                        </Button>
                      </Tooltip>
                      <Rate 
                        size="small" 
                        value={messageFeedback[msg.id]?.rating || 0}
                        onChange={(rating) => handleRatingFeedback(msg.id, msg, rating)}
                        disabled={messageFeedback[msg.id]?.rating !== undefined || feedbackLoading}
                        style={{ fontSize: 14 }}
                      />
                    </Space>
                  </div>
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
