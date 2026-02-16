import { useEffect, useState } from 'react';
import { Table, Card, Tag, Typography, Select, Space, Button, Drawer, Descriptions, Tabs, Modal, Form, Input, InputNumber, Switch, Row, Col, message, TimePicker } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { alertService } from '../services/alerts';
import { databaseService } from '../services/databases';
import type { DatabaseItem } from '../services/databases';
import type { Alert, AlertRule } from '../services/alerts';

const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };
const statusColor: Record<string, string> = { firing: 'red', resolved: 'green', acknowledged: 'blue' };

export default function AlertList() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [ruleType, setRuleType] = useState<string>('metric');
  const [dbList, setDbList] = useState<DatabaseItem[]>([]);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

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

  const fetchRules = async () => {
    setRulesLoading(true);
    try {
      const { data } = await alertService.listRules();
      setRules(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setRulesLoading(false); }
  };

  const loadDbList = async () => {
    try {
      const { data } = await databaseService.list();
      setDbList(data.databases || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchAlerts(); }, [page, statusFilter, severityFilter]);

  const handleAck = async (id: string) => {
    try {
      await alertService.ack(id);
      messageApi.success('已确认');
      fetchAlerts();
      setSelectedAlert(null);
    } catch { messageApi.error('操作失败'); }
  };

  const handleRuleSave = async (values: Record<string, unknown>) => {
    const payload = { ...values } as Record<string, unknown>;
    // Convert dayjs TimePicker values to HH:mm strings
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

  const alertColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '严重级别', dataIndex: 'severity', render: (s: string) => <Tag color={severityColor[s]}>{s}</Tag> },
    { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={statusColor[s]}>{s}</Tag> },
    { title: '触发时间', dataIndex: 'fired_at', render: (t: string) => new Date(t).toLocaleString() },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: Alert) => (
        <Space>
          <Button type="link" size="small" onClick={() => setSelectedAlert(record)}>详情</Button>
          {record.status === 'firing' && <Button type="link" size="small" onClick={() => handleAck(record.id)}>确认</Button>}
        </Space>
      ),
    },
  ];

  const ruleTypeLabel: Record<string, string> = { metric: '指标', log_keyword: '日志关键字', db_metric: '数据库' };
  const ruleTypeColor: Record<string, string> = { metric: 'blue', log_keyword: 'purple', db_metric: 'cyan' };

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
            if (r.silence_start) vals.silence_start = dayjs(r.silence_start, 'HH:mm:ss');
            if (r.silence_end) vals.silence_end = dayjs(r.silence_end, 'HH:mm:ss');
            form.setFieldsValue(vals);
            loadDbList();
            setRuleModalOpen(true);
          }}>编辑</Button>
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

          {/* Metric fields */}
          {ruleType === 'metric' && (
            <Form.Item name="metric" label="指标" rules={[{ required: true }]}>
              <Select options={[
                { label: 'CPU 使用率', value: 'cpu_percent' },
                { label: '内存使用率', value: 'memory_percent' },
                { label: '磁盘使用率', value: 'disk_percent' },
              ]} />
            </Form.Item>
          )}

          {/* Log keyword fields */}
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

          {/* Database metric fields */}
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

          {/* Shared threshold fields for metric and db_metric */}
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
          <Form.Item name="silence_start" label="静默开始">
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="silence_end" label="静默结束">
            <TimePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
