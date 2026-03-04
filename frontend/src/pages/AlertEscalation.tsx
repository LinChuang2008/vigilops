/**
 * 告警升级管理页面
 *
 * 包含三个 Tab：
 * 1. 升级规则 - 升级规则 CRUD 管理
 * 2. 升级历史 - 升级记录查询
 * 3. 升级统计 - 统计图表
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, InputNumber, Switch, Select,
  Tag, Space, Tabs, message, Popconfirm, DatePicker, Row, Col, Statistic, Typography,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ArrowUpOutlined,
  ReloadOutlined, ThunderboltOutlined, BarChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { escalationService } from '../services/escalation';

const { RangePicker } = DatePicker;
const { Title } = Typography;

const severityColor: Record<string, string> = { critical: 'red', warning: 'orange', info: 'blue' };

interface EscalationLevel {
  level: number;
  delay_minutes: number;
  severity: string;
}

interface EscalationRule {
  id: number;
  alert_rule_id: number;
  name: string;
  is_enabled: boolean;
  escalation_levels: EscalationLevel[];
  created_at: string;
  updated_at: string;
}

interface EscalationHistory {
  id: number;
  alert_id: number;
  escalation_rule_id: number | null;
  from_severity: string;
  to_severity: string;
  escalation_level: number;
  escalated_by_system: boolean;
  message: string | null;
  escalated_at: string;
}

interface EscalationStats {
  total_escalations: number;
  today_escalations: number;
  escalations_by_severity: Record<string, number>;
  escalations_by_level: Record<string, number>;
}

export default function AlertEscalation() {
  const { t } = useTranslation();
  const [messageApi, contextHolder] = message.useMessage();

  const severityOptions = [
    { value: 'info', label: t('alertEscalation.severityInfo') },
    { value: 'warning', label: t('alertEscalation.severityWarning') },
    { value: 'critical', label: t('alertEscalation.severityCritical') },
  ];

  // ===== 升级规则 =====
  const [rules, setRules] = useState<EscalationRule[]>([]);
  const [rulesTotal, setRulesTotal] = useState(0);
  const [rulesPage, setRulesPage] = useState(1);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<EscalationRule | null>(null);
  const [ruleForm] = Form.useForm();

  // ===== 升级历史 =====
  const [history, setHistory] = useState<EscalationHistory[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDateRange, setHistoryDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  // ===== 手动升级 =====
  const [escalateModalOpen, setEscalateModalOpen] = useState(false);
  const [escalateForm] = Form.useForm();

  // ===== 统计 =====
  const [stats, setStats] = useState<EscalationStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // ===== 数据加载 =====
  const fetchRules = useCallback(async () => {
    setRulesLoading(true);
    try {
      const { data } = await escalationService.listRules({ page: rulesPage, page_size: 20 });
      setRules(data.items || []);
      setRulesTotal(data.total || 0);
    } catch { /* ignore */ } finally { setRulesLoading(false); }
  }, [rulesPage]);

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const params: Record<string, unknown> = { page: historyPage, page_size: 20 };
      if (historyDateRange) {
        params.start_date = historyDateRange[0].format('YYYY-MM-DD');
        params.end_date = historyDateRange[1].format('YYYY-MM-DD');
      }
      const { data } = await escalationService.listHistory(params);
      setHistory(data.items || []);
      setHistoryTotal(data.total || 0);
    } catch { /* ignore */ } finally { setHistoryLoading(false); }
  }, [historyPage, historyDateRange]);

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const { data } = await escalationService.getStats();
      setStats(data);
    } catch { /* ignore */ } finally { setStatsLoading(false); }
  }, []);

  useEffect(() => { fetchRules(); }, [fetchRules]);
  useEffect(() => { fetchHistory(); }, [fetchHistory]);
  useEffect(() => { fetchStats(); }, [fetchStats]);

  // ===== 规则 CRUD =====
  const openRuleModal = (rule?: EscalationRule) => {
    setEditingRule(rule || null);
    if (rule) {
      ruleForm.setFieldsValue({
        ...rule,
        escalation_levels: rule.escalation_levels,
      });
    } else {
      ruleForm.resetFields();
      ruleForm.setFieldsValue({
        is_enabled: true,
        escalation_levels: [{ level: 1, delay_minutes: 30, severity: 'warning' }],
      });
    }
    setRuleModalOpen(true);
  };

  const handleRuleSave = async () => {
    try {
      const values = await ruleForm.validateFields();
      if (editingRule) {
        await escalationService.updateRule(editingRule.id, values);
        messageApi.success(t('alertEscalation.ruleUpdated'));
      } else {
        await escalationService.createRule(values);
        messageApi.success(t('alertEscalation.ruleCreated'));
      }
      setRuleModalOpen(false);
      fetchRules();
    } catch { /* validation error */ }
  };

  const handleRuleDelete = async (id: number) => {
    try {
      await escalationService.deleteRule(id);
      messageApi.success(t('alertEscalation.ruleDeleted'));
      fetchRules();
    } catch { messageApi.error(t('alertEscalation.deleteFailed')); }
  };

  // ===== 手动升级 =====
  const handleManualEscalate = async () => {
    try {
      const values = await escalateForm.validateFields();
      await escalationService.manualEscalate(values.alert_id, {
        to_severity: values.to_severity,
        message: values.message,
      });
      messageApi.success(t('alertEscalation.escalated'));
      setEscalateModalOpen(false);
      escalateForm.resetFields();
      fetchHistory();
      fetchStats();
    } catch (err: any) {
      messageApi.error(err?.response?.data?.detail || t('alertEscalation.escalateFailed'));
    }
  };

  // ===== 引擎扫描 =====
  const handleTriggerScan = async () => {
    try {
      await escalationService.triggerScan();
      messageApi.success(t('alertEscalation.scanTriggered'));
      fetchHistory();
      fetchStats();
    } catch { messageApi.error(t('alertEscalation.scanFailed')); }
  };

  // ===== 表格列定义 =====
  const ruleColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: t('alertEscalation.columnRuleName'), dataIndex: 'name', ellipsis: true },
    { title: t('alertEscalation.columnAlertRuleId'), dataIndex: 'alert_rule_id', width: 100 },
    {
      title: t('alertEscalation.columnStatus'), dataIndex: 'is_enabled', width: 80,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? t('alertEscalation.statusEnabled') : t('alertEscalation.statusDisabled')}</Tag>,
    },
    {
      title: t('alertEscalation.columnLevel'), dataIndex: 'escalation_levels',
      render: (levels: EscalationLevel[]) => (
        <Space size={4} wrap>
          {levels?.map((l) => (
            <Tag key={l.level} color={severityColor[l.severity]}>
              L{l.level}: {l.delay_minutes}{t('alertEscalation.minuteUnit')} → {l.severity}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('alertEscalation.columnCreatedAt'), dataIndex: 'created_at', width: 170,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('common.actions'), width: 120, fixed: 'right' as const,
      render: (_: unknown, record: EscalationRule) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openRuleModal(record)} />
          <Popconfirm title={t('alertEscalation.confirmDeleteRule')} onConfirm={() => handleRuleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const historyColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: t('alertEscalation.columnAlertId'), dataIndex: 'alert_id', width: 80 },
    {
      title: t('alertEscalation.columnEscalation'), width: 200,
      render: (_: unknown, record: EscalationHistory) => (
        <Space>
          <Tag color={severityColor[record.from_severity]}>{record.from_severity}</Tag>
          <ArrowUpOutlined />
          <Tag color={severityColor[record.to_severity]}>{record.to_severity}</Tag>
        </Space>
      ),
    },
    { title: t('alertEscalation.columnLevelNum'), dataIndex: 'escalation_level', width: 60, render: (v: number) => `L${v}` },
    {
      title: t('alertEscalation.columnType'), dataIndex: 'escalated_by_system', width: 80,
      render: (v: boolean) => <Tag color={v ? 'blue' : 'purple'}>{v ? t('alertEscalation.typeAuto') : t('alertEscalation.typeManual')}</Tag>,
    },
    { title: t('alertEscalation.columnMessage'), dataIndex: 'message', ellipsis: true },
    {
      title: t('alertEscalation.columnEscalatedAt'), dataIndex: 'escalated_at', width: 170,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  return (
    <>
      {contextHolder}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>{t('alertEscalation.title')}</Title>
        <Space>
          <Button icon={<ThunderboltOutlined />} onClick={handleTriggerScan}>{t('alertEscalation.triggerScan')}</Button>
          <Button icon={<ArrowUpOutlined />} onClick={() => { escalateForm.resetFields(); setEscalateModalOpen(true); }}>
            {t('alertEscalation.manualEscalate')}
          </Button>
        </Space>
      </div>

      <Tabs
        items={[
          {
            key: 'rules',
            label: t('alertEscalation.rules'),
            children: (
              <Card
                extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => openRuleModal()}>{t('alertEscalation.newRule')}</Button>}
              >
                <Table
                  rowKey="id"
                  columns={ruleColumns}
                  dataSource={rules}
                  loading={rulesLoading}
                  pagination={{ current: rulesPage, total: rulesTotal, pageSize: 20, onChange: setRulesPage }}
                  scroll={{ x: 900 }}
                  size="small"
                />
              </Card>
            ),
          },
          {
            key: 'history',
            label: t('alertEscalation.history'),
            children: (
              <Card
                extra={
                  <Space>
                    <RangePicker
                      value={historyDateRange}
                      onChange={(dates) => { setHistoryDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null); setHistoryPage(1); }}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchHistory} />
                  </Space>
                }
              >
                <Table
                  rowKey="id"
                  columns={historyColumns}
                  dataSource={history}
                  loading={historyLoading}
                  pagination={{ current: historyPage, total: historyTotal, pageSize: 20, onChange: setHistoryPage }}
                  scroll={{ x: 800 }}
                  size="small"
                />
              </Card>
            ),
          },
          {
            key: 'stats',
            label: t('alertEscalation.stats'),
            children: (
              <Card loading={statsLoading} extra={<Button icon={<ReloadOutlined />} onClick={fetchStats} />}>
                {stats && (
                  <>
                    <Row gutter={16} style={{ marginBottom: 24 }}>
                      <Col span={6}>
                        <Card bordered={false}><Statistic title={t('alertEscalation.totalEscalations')} value={stats.total_escalations} prefix={<BarChartOutlined />} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card bordered={false}><Statistic title={t('alertEscalation.todayEscalations')} value={stats.today_escalations} prefix={<ArrowUpOutlined />} valueStyle={{ color: stats.today_escalations > 0 ? '#cf1322' : undefined }} /></Card>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Card title={t('alertEscalation.bySeverity')} bordered={false} size="small">
                          {Object.entries(stats.escalations_by_severity).length === 0
                            ? <Typography.Text type="secondary">{t('alertEscalation.noData')}</Typography.Text>
                            : Object.entries(stats.escalations_by_severity).map(([sev, count]) => (
                                <div key={sev} style={{ marginBottom: 8 }}>
                                  <Tag color={severityColor[sev]}>{sev}</Tag> <strong>{count}</strong> {t('common.times')}
                                </div>
                              ))
                          }
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card title={t('alertEscalation.byLevel')} bordered={false} size="small">
                          {Object.entries(stats.escalations_by_level).length === 0
                            ? <Typography.Text type="secondary">{t('alertEscalation.noData')}</Typography.Text>
                            : Object.entries(stats.escalations_by_level).map(([level, count]) => (
                                <div key={level} style={{ marginBottom: 8 }}>
                                  <Tag color="geekblue">L{level}</Tag> <strong>{count}</strong> {t('common.times')}
                                </div>
                              ))
                          }
                        </Card>
                      </Col>
                    </Row>
                  </>
                )}
              </Card>
            ),
          },
        ]}
      />

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? t('alertEscalation.editRule') : t('alertEscalation.newRuleTitle')}
        open={ruleModalOpen}
        onOk={handleRuleSave}
        onCancel={() => setRuleModalOpen(false)}
        width={window.innerWidth < 768 ? '100%' : 640}
        destroyOnClose
      >
        <Form form={ruleForm} layout="vertical">
          <Form.Item name="name" label={t('alertEscalation.ruleName')} rules={[{ required: true, message: t('alertEscalation.ruleNameRequired') }]}>
            <Input placeholder={t('alertEscalation.exampleRuleName')} />
          </Form.Item>
          <Form.Item name="alert_rule_id" label={t('alertEscalation.alertRuleId')} rules={[{ required: true, message: t('alertEscalation.alertRuleIdRequired') }]}>
            <InputNumber style={{ width: '100%' }} min={1} placeholder={t('alertEscalation.alertRuleId')} />
          </Form.Item>
          <Form.Item name="is_enabled" label={t('alertEscalation.enabledLabel')} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.List name="escalation_levels">
            {(fields, { add, remove }) => (
              <>
                <div style={{ marginBottom: 8, fontWeight: 500 }}>{t('alertEscalation.escalationLevels')}</div>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} align="baseline" style={{ display: 'flex', marginBottom: 8 }}>
                    <Form.Item {...restField} name={[name, 'level']} rules={[{ required: true }]}>
                      <InputNumber placeholder={t('alertEscalation.level')} min={1} style={{ width: 80 }} addonBefore="L" />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'delay_minutes']} rules={[{ required: true }]}>
                      <InputNumber placeholder={t('alertEscalation.delayMinutes')} min={1} style={{ width: 140 }} addonAfter={t('alertEscalation.minuteUnit')} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'severity']} rules={[{ required: true }]}>
                      <Select placeholder={t('alertEscalation.targetSeverity')} style={{ width: 120 }} options={severityOptions} />
                    </Form.Item>
                    {fields.length > 1 && (
                      <Button type="link" danger onClick={() => remove(name)} icon={<DeleteOutlined />} />
                    )}
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ level: fields.length + 1, delay_minutes: 30, severity: 'critical' })} icon={<PlusOutlined />} block>
                  {t('alertEscalation.addLevel')}
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      {/* 手动升级弹窗 */}
      <Modal
        title={t('alertEscalation.manualEscalateTitle')}
        open={escalateModalOpen}
        onOk={handleManualEscalate}
        onCancel={() => setEscalateModalOpen(false)}
        destroyOnClose
      >
        <Form form={escalateForm} layout="vertical">
          <Form.Item name="alert_id" label={t('alertEscalation.alertId')} rules={[{ required: true, message: t('alertEscalation.alertIdRequired') }]}>
            <InputNumber style={{ width: '100%' }} min={1} placeholder={t('alertEscalation.alertId')} />
          </Form.Item>
          <Form.Item name="to_severity" label={t('alertEscalation.targetSeverity')} rules={[{ required: true, message: t('alertEscalation.targetSeverityRequired') }]}>
            <Select placeholder={t('alertEscalation.targetSeverity')} options={severityOptions} />
          </Form.Item>
          <Form.Item name="message" label={t('alertEscalation.reason')}>
            <Input.TextArea rows={3} placeholder={t('alertEscalation.reason')} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
