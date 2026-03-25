import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Divider,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import PageHeader from '../components/PageHeader';
import {
  customRunbookService,
  type CreateRunbookRequest,
  type CustomRunbook,
  type DryRunResponse,
  type GenerateRunbookResponse,
  type RunbookListItem,
} from '../services/customRunbook';

const { Paragraph, Text } = Typography;

const RISK_OPTIONS = [
  { label: 'auto', value: 'auto' },
  { label: 'confirm', value: 'confirm' },
  { label: 'manual', value: 'manual' },
  { label: 'block', value: 'block' },
];

type DetailState = CustomRunbook | null;

function riskColor(level: string) {
  if (level === 'auto') return 'green';
  if (level === 'confirm') return 'gold';
  if (level === 'manual') return 'orange';
  return 'red';
}

function toKeywordArray(raw?: string) {
  return (raw || '')
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function safeFileName() {
  return `custom_runbooks_${new Date().toISOString().slice(0, 10)}.json`;
}

export default function RunbookManagement() {
  const [rows, setRows] = useState<RunbookListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<DetailState>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorLoading, setEditorLoading] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<GenerateRunbookResponse | null>(null);
  const [dryRunOpen, setDryRunOpen] = useState(false);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<DryRunResponse | null>(null);
  const [selectedCustom, setSelectedCustom] = useState<CustomRunbook | null>(null);
  const [messageApi, contextHolder] = message.useMessage();

  const [editorForm] = Form.useForm();
  const [aiForm] = Form.useForm();
  const [dryRunForm] = Form.useForm();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const userRole = localStorage.getItem('user_role') || 'viewer';
  const canEdit = userRole === 'admin' || userRole === 'operator';
  const canDelete = userRole === 'admin';

  const load = async () => {
    setLoading(true);
    try {
      const res = await customRunbookService.listAll();
      setRows(res.data.items || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filteredRows = useMemo(() => rows, [rows]);

  const openCreate = () => {
    setSelectedCustom(null);
    editorForm.resetFields();
    editorForm.setFieldsValue({
      risk_level: 'manual',
      is_active: true,
      trigger_keywords_text: '',
      safety_checks_text: '',
      steps: [{ name: '步骤 1', command: '', timeout_sec: 30, rollback_command: '' }],
    });
    setEditorOpen(true);
  };

  const openEdit = async (row: RunbookListItem) => {
    setEditorLoading(true);
    try {
      const res = await customRunbookService.get(row.id);
      const data = res.data;
      setSelectedCustom(data);
      editorForm.setFieldsValue({
        name: data.name,
        description: data.description,
        risk_level: data.risk_level,
        is_active: data.is_active,
        trigger_keywords_text: (data.trigger_keywords || []).join(', '),
        safety_checks_text: (data.safety_checks || []).join('\n'),
        steps: (data.steps || []).map((step: any) => ({
          name: step.name,
          command: step.command,
          timeout_sec: step.timeout_sec,
          rollback_command: step.rollback_command || '',
        })),
      });
      setEditorOpen(true);
    } finally {
      setEditorLoading(false);
    }
  };

  const openDetail = async (row: RunbookListItem) => {
    setDetailLoading(true);
    setDetailOpen(true);
    try {
      const res = await customRunbookService.get(row.id);
      setDetail(res.data);
    } finally {
      setDetailLoading(false);
    }
  };

  const saveRunbook = async () => {
    const values = await editorForm.validateFields();
    const payload: CreateRunbookRequest = {
      name: values.name.trim(),
      description: values.description || '',
      risk_level: values.risk_level,
      is_active: !!values.is_active,
      trigger_keywords: toKeywordArray(values.trigger_keywords_text),
      safety_checks: toKeywordArray(values.safety_checks_text),
      steps: (values.steps || []).map((step: any) => ({
        name: step.name,
        command: step.command,
        timeout_sec: Number(step.timeout_sec || 30),
        rollback_command: step.rollback_command || null,
      })),
    };

    setEditorLoading(true);
    try {
      if (selectedCustom) {
        await customRunbookService.update(selectedCustom.id, payload);
        messageApi.success('Runbook 已更新');
      } else {
        await customRunbookService.create(payload);
        messageApi.success('Runbook 已创建');
      }
      setEditorOpen(false);
      await load();
    } finally {
      setEditorLoading(false);
    }
  };

  const deleteRunbook = async (row: RunbookListItem) => {
    if (!row.id) return;
    await customRunbookService.delete(row.id);
    messageApi.success('Runbook 已删除');
    await load();
  };

  const exportRunbooks = async () => {
    const res = await customRunbookService.exportAll();
    const blob = res.data instanceof Blob
      ? res.data
      : new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = safeFileName();
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const importRunbooks = async (file: File) => {
    await customRunbookService.importFile(file);
    messageApi.success('Runbook 导入完成');
    await load();
  };

  const generateWithAI = async () => {
    const values = await aiForm.validateFields();
    setAiLoading(true);
    try {
      const res = await customRunbookService.generateWithAI({
        description: values.description,
        risk_level: values.risk_level,
      });
      setAiResult(res.data);
      if (res.data.success && res.data.runbook) {
        editorForm.setFieldsValue({
          name: res.data.runbook.name,
          description: res.data.runbook.description,
          risk_level: res.data.runbook.risk_level || values.risk_level || 'manual',
          is_active: true,
          trigger_keywords_text: (res.data.runbook.trigger_keywords || []).join(', '),
          safety_checks_text: '',
          steps: (res.data.runbook.steps || []).map((step) => ({
            name: step.name,
            command: step.command,
            timeout_sec: step.timeout_sec,
            rollback_command: step.rollback_command || '',
          })),
        });
      }
    } finally {
      setAiLoading(false);
    }
  };

  const useAiResult = () => {
    setSelectedCustom(null);
    setAiOpen(false);
    setEditorOpen(true);
  };

  const openDryRun = async (row: RunbookListItem) => {
    const res = await customRunbookService.get(row.id);
    setSelectedCustom(res.data);
    dryRunForm.setFieldsValue({ variables_json: '{}' });
    setDryRunResult(null);
    setDryRunOpen(true);
  };

  const runDryRun = async () => {
    if (!selectedCustom) return;
    const values = await dryRunForm.validateFields();
    let variables: Record<string, string> = {};
    try {
      variables = JSON.parse(values.variables_json || '{}');
    } catch {
      messageApi.error('变量 JSON 格式不正确');
      return;
    }

    setDryRunLoading(true);
    try {
      const res = await customRunbookService.dryRun(selectedCustom.id, variables);
      setDryRunResult(res.data);
    } finally {
      setDryRunLoading(false);
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      render: (_: unknown, row: RunbookListItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{row.name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.description || '-'}</Text>
        </Space>
      ),
    },
    {
      title: '风险',
      dataIndex: 'risk_level',
      width: 100,
      render: (value: string) => <Tag color={riskColor(value)}>{value}</Tag>,
    },
    {
      title: '匹配',
      width: 220,
      render: (_: unknown, row: RunbookListItem) => {
        const items = row.trigger_keywords || [];
        return items.length ? (
          <Text style={{ fontSize: 12 }}>{items.slice(0, 4).join(', ')}{items.length > 4 ? ' ...' : ''}</Text>
        ) : '-';
      },
    },
    {
      title: '步骤数',
      dataIndex: 'steps_count',
      width: 90,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      render: (value: boolean) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag>,
    },
    {
      title: '操作',
      width: 260,
      render: (_: unknown, row: RunbookListItem) => (
        <Space wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(row)}>查看</Button>
          <Button size="small" onClick={() => openDryRun(row)}>Dry-run</Button>
          {canEdit && (
            <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
          )}
          {canDelete && (
            <Popconfirm title="确认删除该 Runbook？" onConfirm={() => deleteRunbook(row)}>
              <Button size="small" danger>删除</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {contextHolder}
      <PageHeader title="Runbook 管理" />
      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          {canEdit && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建 Runbook</Button>}
          {canEdit && <Button icon={<RobotOutlined />} onClick={() => { setAiResult(null); aiForm.resetFields(); aiForm.setFieldsValue({ risk_level: 'manual' }); setAiOpen(true); }}>AI 生成</Button>}
          <Button icon={<DownloadOutlined />} onClick={exportRunbooks}>导出自定义</Button>
          {canDelete && (
            <>
              <Button icon={<UploadOutlined />} onClick={() => fileInputRef.current?.click()}>导入自定义</Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                style={{ display: 'none' }}
                onChange={async (event) => {
                  const file = event.target.files?.[0];
                  event.currentTarget.value = '';
                  if (!file) return;
                  await importRunbooks(file);
                }}
              />
            </>
          )}
        </Space>

        <Table
          rowKey={(row) => `${row.id}`}
          loading={loading}
          dataSource={filteredRows}
          columns={columns}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Drawer
        title="Runbook 详情"
        width={860}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {detailLoading && <Text type="secondary">加载中...</Text>}
        {!detailLoading && detail && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="说明">{detail.description || '-'}</Descriptions.Item>
              <Descriptions.Item label="风险"><Tag color={riskColor(detail.risk_level)}>{detail.risk_level}</Tag></Descriptions.Item>
              <Descriptions.Item label="触发关键词">{(detail.trigger_keywords || []).join(', ') || '-'}</Descriptions.Item>
              <Descriptions.Item label="安全检查">{(detail.safety_checks || []).join(', ') || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">{detail.is_active ? '启用' : '停用'}</Descriptions.Item>
            </Descriptions>
            <Table
              size="small"
              pagination={false}
              rowKey={(_, index) => `step-${index}`}
              dataSource={detail.steps || []}
              columns={[
                { title: '名称', dataIndex: 'name', width: 150 },
                { title: '命令', dataIndex: 'command' },
                { title: '超时', dataIndex: 'timeout_sec', width: 80 },
                { title: '回滚', dataIndex: 'rollback_command', width: 220, render: (value: string) => value || '-' },
              ]}
            />
          </Space>
        )}
      </Drawer>

      <Modal
        title={selectedCustom ? '编辑自定义 Runbook' : '新建自定义 Runbook'}
        open={editorOpen}
        onCancel={() => setEditorOpen(false)}
        onOk={saveRunbook}
        confirmLoading={editorLoading}
        width={980}
      >
        <Form form={editorForm} layout="vertical">
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如 nginx_restart_custom" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Space style={{ width: '100%' }} align="start">
            <Form.Item label="风险等级" name="risk_level" rules={[{ required: true }]} style={{ minWidth: 160 }}>
              <Select options={RISK_OPTIONS} />
            </Form.Item>
            <Form.Item label="启用" name="is_active" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item label="触发关键词" name="trigger_keywords_text" extra="用逗号或换行分隔">
            <Input.TextArea rows={2} placeholder="nginx, upstream, 502" />
          </Form.Item>
          <Form.Item label="安全检查" name="safety_checks_text" extra="用逗号或换行分隔">
            <Input.TextArea rows={2} placeholder={'service must exist\ndisk usage > 80%'} />
          </Form.Item>

          <Divider>步骤</Divider>
          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    title={`步骤 ${index + 1}`}
                    style={{ marginBottom: 12 }}
                    extra={fields.length > 1 ? <Button danger size="small" onClick={() => remove(field.name)}>删除</Button> : null}
                  >
                    <Form.Item name={[field.name, 'name']} label="步骤名称" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item name={[field.name, 'command']} label="执行命令" rules={[{ required: true }]}>
                      <Input.TextArea rows={3} />
                    </Form.Item>
                    <Space style={{ width: '100%' }} align="start">
                      <Form.Item name={[field.name, 'timeout_sec']} label="超时（秒）" initialValue={30} rules={[{ required: true }]} style={{ minWidth: 160 }}>
                        <InputNumber min={1} max={3600} style={{ width: '100%' }} />
                      </Form.Item>
                    </Space>
                    <Form.Item name={[field.name, 'rollback_command']} label="回滚命令">
                      <Input.TextArea rows={2} />
                    </Form.Item>
                  </Card>
                ))}
                <Button type="dashed" block onClick={() => add({ name: `步骤 ${fields.length + 1}`, command: '', timeout_sec: 30, rollback_command: '' })}>
                  新增步骤
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal
        title="AI 生成 Runbook"
        open={aiOpen}
        onCancel={() => setAiOpen(false)}
        onOk={generateWithAI}
        confirmLoading={aiLoading}
        width={860}
      >
        <Form form={aiForm} layout="vertical">
          <Form.Item label="场景描述" name="description" rules={[{ required: true, message: '请描述运维场景' }]}>
            <Input.TextArea rows={5} placeholder="例如：Nginx upstream 频繁 502，希望先检查配置、连接状态，再做安全重载。" />
          </Form.Item>
          <Form.Item label="预设风险等级" name="risk_level">
            <Select options={RISK_OPTIONS} />
          </Form.Item>
        </Form>
        {aiResult && (
          <>
            <Divider />
            {aiResult.success && aiResult.runbook ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text strong>{aiResult.runbook.name}</Text>
                <Paragraph style={{ marginBottom: 0 }}>{aiResult.runbook.description}</Paragraph>
                {aiResult.safety_warnings?.length > 0 && (
                  <div>
                    <Text strong>安全提示</Text>
                    {(aiResult.safety_warnings || []).map((warning, index) => (
                      <div key={index}><Text type="warning">- {warning}</Text></div>
                    ))}
                  </div>
                )}
                <Button type="primary" onClick={useAiResult}>载入编辑器</Button>
              </Space>
            ) : (
              <Text type="danger">{aiResult.error || '生成失败'}</Text>
            )}
          </>
        )}
      </Modal>

      <Modal
        title={selectedCustom ? `Dry-run: ${selectedCustom.name}` : 'Dry-run'}
        open={dryRunOpen}
        onCancel={() => setDryRunOpen(false)}
        onOk={runDryRun}
        confirmLoading={dryRunLoading}
        width={980}
      >
        <Form form={dryRunForm} layout="vertical">
          <Form.Item
            label="变量 JSON"
            name="variables_json"
            extra='例如 {"service_name":"nginx","host":"10.0.0.1"}'
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>

        {dryRunResult && (
          <>
            <Divider />
            <Space style={{ marginBottom: 12 }}>
              <Tag color={riskColor(dryRunResult.risk_level)}>{dryRunResult.risk_level}</Tag>
              <Tag color={dryRunResult.all_safe ? 'green' : 'red'}>
                {dryRunResult.all_safe ? '全部安全检查通过' : '存在风险步骤'}
              </Tag>
              <Text type="secondary">共 {dryRunResult.total_steps} 步</Text>
            </Space>
            <Table
              size="small"
              pagination={false}
              rowKey={(row) => row.step_name}
              dataSource={dryRunResult.steps}
              columns={[
                { title: '步骤', dataIndex: 'step_name', width: 140 },
                { title: '命令', dataIndex: 'resolved_command' },
                { title: '超时', dataIndex: 'timeout_sec', width: 80 },
                {
                  title: '安全检查',
                  width: 160,
                  render: (_: unknown, row: any) => (
                    <Space direction="vertical" size={0}>
                      <Tag color={row.safety_check_passed ? 'green' : 'red'}>
                        {row.safety_check_passed ? '通过' : '失败'}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>{row.safety_message}</Text>
                    </Space>
                  ),
                },
              ]}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
