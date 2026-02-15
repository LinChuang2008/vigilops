import { useEffect, useState } from 'react';
import { Table, Card, Tag, Typography, Select, Space, Button, Drawer, Descriptions, Tabs, Modal, Form, Input, InputNumber, Switch, Row, Col, message } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { alertService } from '../services/alerts';
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

  useEffect(() => { fetchAlerts(); }, [page, statusFilter, severityFilter]);

  const handleAck = async (id: string) => {
    try {
      await alertService.ack(id);
      messageApi.success('已确认');
      fetchAlerts();
      setSelectedAlert(null);
    } catch { messageApi.error('操作失败'); }
  };

  const handleRuleSave = async (values: Partial<AlertRule>) => {
    try {
      if (editingRule) {
        await alertService.updateRule(editingRule.id, values);
      } else {
        await alertService.createRule(values);
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
    { title: '触发时间', dataIndex: 'triggered_at', render: (t: string) => new Date(t).toLocaleString() },
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

  const ruleColumns = [
    { title: '名称', dataIndex: 'name' },
    { title: '指标', dataIndex: 'metric' },
    { title: '条件', key: 'cond', render: (_: unknown, r: AlertRule) => `${r.operator} ${r.threshold}` },
    { title: '持续(秒)', dataIndex: 'duration_seconds' },
    { title: '级别', dataIndex: 'severity', render: (s: string) => <Tag color={severityColor[s]}>{s}</Tag> },
    { title: '启用', dataIndex: 'enabled', render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? '是' : '否'}</Tag> },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: AlertRule) => (
        <Space>
          <Button type="link" size="small" onClick={() => { setEditingRule(r); form.setFieldsValue(r); setRuleModalOpen(true); }}>编辑</Button>
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
                <Button type="primary" onClick={() => { setEditingRule(null); form.resetFields(); setRuleModalOpen(true); }}>新建规则</Button>
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
            <Descriptions.Item label="触发时间">{new Date(selectedAlert.triggered_at).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="恢复时间">{selectedAlert.resolved_at ? new Date(selectedAlert.resolved_at).toLocaleString() : '-'}</Descriptions.Item>
            <Descriptions.Item label="确认时间">{selectedAlert.acknowledged_at ? new Date(selectedAlert.acknowledged_at).toLocaleString() : '-'}</Descriptions.Item>
          </Descriptions>
        )}
        {selectedAlert?.status === 'firing' && (
          <Button type="primary" style={{ marginTop: 16 }} onClick={() => handleAck(selectedAlert.id)}>确认告警</Button>
        )}
      </Drawer>

      <Modal title={editingRule ? '编辑规则' : '新建规则'} open={ruleModalOpen} onCancel={() => setRuleModalOpen(false)}
        onOk={() => form.submit()} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleRuleSave}>
          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="metric" label="指标" rules={[{ required: true }]}>
            <Select options={[
              { label: 'CPU 使用率', value: 'cpu_percent' },
              { label: '内存使用率', value: 'memory_percent' },
              { label: '磁盘使用率', value: 'disk_percent' },
            ]} />
          </Form.Item>
          <Form.Item name="operator" label="运算符" rules={[{ required: true }]}>
            <Select options={[{ label: '>', value: '>' }, { label: '>=', value: '>=' }, { label: '<', value: '<' }, { label: '<=', value: '<=' }]} />
          </Form.Item>
          <Form.Item name="threshold" label="阈值" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="duration_seconds" label="持续时间(秒)" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="severity" label="严重级别" rules={[{ required: true }]}>
            <Select options={[{ label: 'Critical', value: 'critical' }, { label: 'Warning', value: 'warning' }, { label: 'Info', value: 'info' }]} />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
