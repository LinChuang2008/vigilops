/**
 * 告警中心页面
 *
 * 包含两个 Tab：
 * 1. 告警列表 - 展示所有告警，支持按状态和严重级别筛选，可查看详情、确认告警、触发 AI 根因分析
 * 2. 告警规则 - 管理告警规则（指标告警、日志关键字告警、数据库告警），支持增删改及静默时段设置
 */
import { useEffect, useState } from 'react';
import { Table, Card, Tag, Typography, Select, Space, Button, Drawer, Descriptions, Tabs, Modal, Form, Input, InputNumber, Switch, Row, Col, message, TimePicker, Spin } from 'antd';
import { ExclamationCircleOutlined, RobotOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api from '../services/api';
import { alertService } from '../services/alerts';
import { databaseService } from '../services/databases';
import type { DatabaseItem } from '../services/databases';
import type { Alert, AlertRule } from '../services/alerts';
import { RemediationStatusTag } from '../components/RemediationBadge';

/** 告警严重级别颜色映射 */
const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };
/** 告警状态颜色映射 */
const statusColor: Record<string, string> = { firing: 'red', resolved: 'green', acknowledged: 'blue' };

/**
 * 告警中心页面组件
 */
export default function AlertList() {
  // ========== 告警列表状态 ==========
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  /** 当前选中的告警（用于侧边详情抽屉） */
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // ========== 告警规则状态 ==========
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  /** 当前编辑的规则（null 表示新建） */
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  /** 当前选择的规则类型，控制表单字段显示 */
  const [ruleType, setRuleType] = useState<string>('metric');
  /** 数据库列表，用于数据库告警规则的下拉选择 */
  const [dbList, setDbList] = useState<DatabaseItem[]>([]);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  // ========== AI 根因分析弹窗 ==========
  const [rcModalOpen, setRcModalOpen] = useState(false);
  const [rcLoading, setRcLoading] = useState(false);
  /** AI 根因分析结果 */
  const [rcData, setRcData] = useState<{ root_cause: string; confidence: string; evidence: string[]; recommendations: string[] } | null>(null);

  /** 触发 AI 根因分析：打开弹窗并请求分析结果 */
  const handleRootCause = async (alertId: string) => {
    setRcData(null);
    setRcModalOpen(true);
    setRcLoading(true);
    try {
      const { data } = await api.post(`/ai/root-cause?alert_id=${alertId}`);
      setRcData(data);
    } catch {
      messageApi.error('AI 分析失败');
      setRcModalOpen(false);
    } finally { setRcLoading(false); }
  };

  /** 获取告警列表，支持分页和筛选 */
  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (statusFilter) params.status = statusFilter;
      if (severityFilter) params.severity = severityFilter;
      const { data } = await alertService.list(params);
      setAlerts(data.items || []);
      setTotal(data.total || 0);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  /** 获取告警规则列表 */
  const fetchRules = async () => {
    setRulesLoading(true);
    try {
      const { data } = await alertService.listRules();
      setRules(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setRulesLoading(false); }
  };

  /** 加载数据库列表，用于数据库告警规则的选择 */
  const loadDbList = async () => {
    try {
      const { data } = await databaseService.list();
      setDbList(data.databases || []);
    } catch { /* ignore */ }
  };

  // 当分页或筛选条件变化时重新获取告警
  useEffect(() => { fetchAlerts(); }, [page, statusFilter, severityFilter]);

  /** 确认告警 */
  const handleAck = async (id: string) => {
    try {
      await alertService.ack(id);
      messageApi.success('已确认');
      fetchAlerts();
      setSelectedAlert(null);
    } catch { messageApi.error('操作失败'); }
  };

  /** 保存告警规则（新建或编辑），处理 TimePicker 值转换 */
  const handleRuleSave = async (values: Record<string, unknown>) => {
    const payload = { ...values } as Record<string, unknown>;
    // 将 dayjs TimePicker 值转为 HH:mm:ss 字符串
    payload.silence_start = values.silence_start ? (values.silence_start as dayjs.Dayjs).format('HH:mm:ss') : null;
    payload.silence_end = values.silence_end ? (values.silence_end as dayjs.Dayjs).format('HH:mm:ss') : null;
    try {
      if (editingRule) {
        await alertService.updateRule(editingRule.id, payload as Partial<AlertRule>);
      } else {
        await alertService.createRule(payload as Partial<AlertRule>);
      }
      messageApi.success('保存成功');
      setRuleModalOpen(false);
      fetchRules();
    } catch { messageApi.error('保存失败'); }
  };

  /** 删除告警规则（带确认弹窗） */
  const handleRuleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除规则？',
      icon: <ExclamationCircleOutlined />,
      onOk: async () => {
        try {
          await alertService.deleteRule(id);
          messageApi.success('已删除');
          fetchRules();
        } catch { messageApi.error('删除失败'); }
      },
    });
  };

  /** 告警列表表格列定义 */
  const alertColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '严重级别', dataIndex: 'severity', render: (s: string) => <Tag color={severityColor[s]}>{s}</Tag> },
    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={statusColor[s]}>{s}</Tag> },
    { title: '触发时间', dataIndex: 'fired_at', render: (t: string) => new Date(t).toLocaleString() },
    {
      title: '修复状态', dataIndex: 'remediation_status', key: 'remediation_status',
      render: (s: string) => s ? <RemediationStatusTag status={s} /> : <span style={{ color: '#999' }}>-</span>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: Alert) => (
        <Space>
          <Button type="link" size="small" onClick={() => setSelectedAlert(record)}>详情</Button>
          {record.status === 'firing' && <Button type="link" size="small" onClick={() => handleAck(record.id)}>确认</Button>}
          <Button type="link" size="small" icon={<RobotOutlined />} onClick={() => handleRootCause(record.id)}>AI 分析</Button>
        </Space>
      ),
    },
  ];

  /** 规则类型中文标签 */
  const ruleTypeLabel: Record<string, string> = { metric: '指标', log_keyword: '日志关键字', db_metric: '数据库' };
  const ruleTypeColor: Record<string, string> = { metric: 'blue', log_keyword: 'purple', db_metric: 'cyan' };

  /** 告警规则表格列定义 */
  const ruleColumns = [
    { title: '名称', dataIndex: 'name' },
    {
      title: '类型', dataIndex: 'rule_type', key: 'rule_type',
      render: (t: string) => <Tag color={ruleTypeColor[t] || 'default'}>{ruleTypeLabel[t] || t || '指标'}</Tag>,
    },
    {
      title: '条件', key: 'cond',
      render: (_: unknown, r: AlertRule) => {
        const rt = r.rule_type || 'metric';
        if (rt === 'log_keyword') return `关键字: ${r.log_keyword || '-'}`;
        if (rt === 'db_metric') return `${r.db_metric_name || '-'} ${r.operator} ${r.threshold}`;
        return `${r.metric} ${r.operator} ${r.threshold}`;
      },
    },
    { title: '级别', dataIndex: 'severity', render: (s: string) => <Tag color={severityColor[s]}>{s}</Tag> },
    { title: '启用', dataIndex: 'is_enabled', render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? '是' : '否'}</Tag> },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: AlertRule) => (
        <Space>
          <Button type="link" size="small" onClick={() => {
            setEditingRule(r);
            setRuleType(r.rule_type || 'metric');
            const vals = { ...r } as Record<string, unknown>;
            // 将字符串时间转为 dayjs 对象以供 TimePicker 使用
            if (r.silence_start) vals.silence_start = dayjs(r.silence_start, 'HH:mm:ss');
            if (r.silence_end) vals.silence_end = dayjs(r.silence_end, 'HH:mm:ss');
            form.setFieldsValue(vals);
            loadDbList();
            setRuleModalOpen(true);
          }}>编辑</Button>
          {/* 内置规则不可删除 */}
          {!r.is_builtin && <Button type="link" size="small" danger onClick={() => handleRuleDelete(r.id)}>删除</Button>}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {contextHolder}
      <Typography.Title level={4}>告警中心</Typography.Title>
      <Tabs defaultActiveKey="alerts" onChange={k => { if (k === 'rules') fetchRules(); }} items={[
        {
          key: 'alerts', label: '告警列表',
          children: (
            <>
              {/* 筛选条件 */}
              <Row style={{ marginBottom: 16 }}>
                <Col>
                  <Space>
                    <Select placeholder="状态" allowClear style={{ width: 120 }} onChange={v => { setStatusFilter(v || ''); setPage(1); }}
                      options={[{ label: '触发中', value: 'firing' }, { label: '已恢复', value: 'resolved' }, { label: '已确认', value: 'acknowledged' }]} />
                    <Select placeholder="级别" allowClear style={{ width: 120 }} onChange={v => { setSeverityFilter(v || ''); setPage(1); }}
                      options={[{ label: 'Critical', value: 'critical' }, { label: 'Warning', value: 'warning' }, { label: 'Info', value: 'info' }]} />
                  </Space>
                </Col>
              </Row>
              <Card>
                <Table dataSource={alerts} columns={alertColumns} rowKey="id" loading={loading}
                  pagination={{ current: page, pageSize: 20, total, onChange: p => setPage(p) }} />
              </Card>
            </>
          ),
        },
        {
          key: 'rules', label: '告警规则',
          children: (
            <>
              <Row justify="end" style={{ marginBottom: 16 }}>
                <Button type="primary" onClick={() => { setEditingRule(null); setRuleType('metric'); form.resetFields(); setRuleModalOpen(true); loadDbList(); }}>新建规则</Button>
              </Row>
              <Card>
                <Table dataSource={rules} columns={ruleColumns} rowKey="id" loading={rulesLoading} pagination={false} />
              </Card>
            </>
          ),
        },
      ]} />

      {/* 告警详情抽屉 */}
      <Drawer open={!!selectedAlert} onClose={() => setSelectedAlert(null)} title="告警详情" width={480}>
        {selectedAlert && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="标题">{selectedAlert.title}</Descriptions.Item>
            <Descriptions.Item label="消息">{selectedAlert.message}</Descriptions.Item>
            <Descriptions.Item label="严重级别"><Tag color={severityColor[selectedAlert.severity]}>{selectedAlert.severity}</Tag></Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColor[selectedAlert.status]}>{selectedAlert.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="触发时间">{new Date(selectedAlert.fired_at).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="恢复时间">{selectedAlert.resolved_at ? new Date(selectedAlert.resolved_at).toLocaleString() : '-'}</Descriptions.Item>
            <Descriptions.Item label="确认时间">{selectedAlert.acknowledged_at ? new Date(selectedAlert.acknowledged_at).toLocaleString() : '-'}</Descriptions.Item>
          </Descriptions>
        )}
        {selectedAlert?.status === 'firing' && (
          <Button type="primary" style={{ marginTop: 16 }} onClick={() => handleAck(selectedAlert.id)}>确认告警</Button>
        )}
      </Drawer>

      {/* 告警规则编辑弹窗 */}
      <Modal title={editingRule ? '编辑规则' : '新建规则'} open={ruleModalOpen} onCancel={() => setRuleModalOpen(false)}
        onOk={() => form.submit()} destroyOnClose width={560}>
        <Form form={form} layout="vertical" onFinish={handleRuleSave} initialValues={{ rule_type: 'metric' }}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="rule_type" label="规则类型" rules={[{ required: true }]}>
            <Select onChange={(v: string) => setRuleType(v)} options={[
              { label: '指标告警', value: 'metric' },
              { label: '日志关键字', value: 'log_keyword' },
              { label: '数据库告警', value: 'db_metric' },
            ]} />
          </Form.Item>

          {/* 指标告警字段 */}
          {ruleType === 'metric' && (
            <Form.Item name="metric" label="指标" rules={[{ required: true }]}>
              <Select options={[
                { label: 'CPU 使用率', value: 'cpu_percent' },
                { label: '内存使用率', value: 'memory_percent' },
                { label: '磁盘使用率', value: 'disk_percent' },
              ]} />
            </Form.Item>
          )}

          {/* 日志关键字告警字段 */}
          {ruleType === 'log_keyword' && (
            <>
              <Form.Item name="log_keyword" label="匹配关键字" rules={[{ required: true }]}><Input placeholder="例如: ERROR, OutOfMemory" /></Form.Item>
              <Form.Item name="log_level" label="日志级别（留空匹配全部）">
                <Select allowClear options={[
                  { label: 'DEBUG', value: 'DEBUG' }, { label: 'INFO', value: 'INFO' },
                  { label: 'WARN', value: 'WARN' }, { label: 'ERROR', value: 'ERROR' }, { label: 'FATAL', value: 'FATAL' },
                ]} />
              </Form.Item>
              <Form.Item name="log_service" label="服务名（留空匹配全部）"><Input placeholder="例如: nginx, app" /></Form.Item>
            </>
          )}

          {/* 数据库告警字段 */}
          {ruleType === 'db_metric' && (
            <>
              <Form.Item name="db_id" label="数据库（留空匹配全部）">
                <Select allowClear options={dbList.map(d => ({ label: `${d.name} (${d.db_type})`, value: d.id }))} />
              </Form.Item>
              <Form.Item name="db_metric_name" label="数据库指标" rules={[{ required: true }]}>
                <Select options={[
                  { label: '连接数', value: 'connections_total' },
                  { label: '活跃连接', value: 'connections_active' },
                  { label: '慢查询', value: 'slow_queries' },
                  { label: '数据库大小(MB)', value: 'database_size_mb' },
                  { label: 'QPS', value: 'qps' },
                ]} />
              </Form.Item>
            </>
          )}

          {/* 指标和数据库告警共用的阈值字段 */}
          {(ruleType === 'metric' || ruleType === 'db_metric') && (
            <>
              <Form.Item name="operator" label="运算符" rules={[{ required: true }]}>
                <Select options={[{ label: '>', value: '>' }, { label: '>=', value: '>=' }, { label: '<', value: '<' }, { label: '<=', value: '<=' }]} />
              </Form.Item>
              <Form.Item name="threshold" label="阈值" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
            </>
          )}

          <Form.Item name="duration_seconds" label="持续时间(秒)"><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="severity" label="严重级别" rules={[{ required: true }]}>
            <Select options={[{ label: 'Critical', value: 'critical' }, { label: 'Warning', value: 'warning' }, { label: 'Info', value: 'info' }]} />
          </Form.Item>
          <Form.Item name="is_enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item name="cooldown_seconds" label="冷却期（秒）" initialValue={300}>
            <InputNumber style={{ width: '100%' }} min={0} placeholder="默认 300 秒" />
          </Form.Item>
          {/* 静默时段设置 */}
          <Form.Item name="silence_start" label="静默开始">
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="silence_end" label="静默结束">
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* AI 根因分析弹窗 */}
      <Modal title={<><RobotOutlined /> AI 根因分析</>} open={rcModalOpen} onCancel={() => setRcModalOpen(false)} footer={null} width={560}>
        {rcLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="AI 正在分析..." /></div>
        ) : rcData ? (
          <div>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="根因">{rcData.root_cause}</Descriptions.Item>
              <Descriptions.Item label="置信度">
                <Tag color={rcData.confidence === 'high' ? 'green' : rcData.confidence === 'medium' ? 'orange' : 'default'}>
                  {rcData.confidence}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
            {rcData.evidence && rcData.evidence.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography.Text strong>证据：</Typography.Text>
                <ul style={{ marginTop: 8 }}>{rcData.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </div>
            )}
            {rcData.recommendations && rcData.recommendations.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography.Text strong>建议操作：</Typography.Text>
                <ul style={{ marginTop: 8 }}>{rcData.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
