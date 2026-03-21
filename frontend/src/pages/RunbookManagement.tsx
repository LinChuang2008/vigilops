/**
 * Runbook 管理页面
 * 列表视图展示所有 Runbook（内置 + 自定义），支持创建、编辑、删除、dry-run
 * 集成 Monaco Editor + AI 生成 Runbook 功能
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card, Table, Button, Tag, Space, Modal, message, Upload, Tooltip,
  Typography, Input, Badge, Popconfirm, Drawer, Form, Select, Switch,
  InputNumber, Divider, Alert, Empty, Spin,
  Tabs,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined,
  DownloadOutlined, UploadOutlined, BookOutlined, SafetyOutlined,
  ThunderboltOutlined, ExperimentOutlined, SearchOutlined,
  RobotOutlined, CodeOutlined, CopyOutlined,
  CheckCircleOutlined, ClockCircleOutlined, WarningOutlined,
  TagsOutlined, UndoOutlined, EyeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import Editor from '@monaco-editor/react';
import {
  customRunbookService,
} from '../services/customRunbook';
import type {
  RunbookListItem,
  RunbookStep,
  CreateRunbookRequest,
  DryRunResponse,
  GenerateRunbookResponse,
} from '../services/customRunbook';

const { Text } = Typography;
const { TextArea } = Input;

const riskLevelColors: Record<string, string> = {
  auto: 'green',
  confirm: 'orange',
  manual: 'blue',
  block: 'red',
};

const riskLevelLabels: Record<string, string> = {
  auto: '自动执行',
  confirm: '需确认',
  manual: '手动触发',
  block: '禁止执行',
};

export default function RunbookManagement() {
  const [loading, setLoading] = useState(false);
  const [allRunbooks, setAllRunbooks] = useState<RunbookListItem[]>([]);
  const [search, setSearch] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [dryRunResult, setDryRunResult] = useState<DryRunResponse | null>(null);
  const [dryRunModalOpen, setDryRunModalOpen] = useState(false);
  const [dryRunLoading, setDryRunLoading] = useState(false);

  // AI 生成相关状态
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiRiskLevel, setAiRiskLevel] = useState('confirm');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiResult, setAiResult] = useState<GenerateRunbookResponse | null>(null);
  const [aiCode, setAiCode] = useState('');
  const editorRef = useRef<any>(null);

  const fetchRunbooks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await customRunbookService.listAll();
      setAllRunbooks(res.data.items);
    } catch {
      message.error('获取 Runbook 列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRunbooks();
  }, [fetchRunbooks]);

  const filtered = allRunbooks.filter(
    (rb) =>
      !search ||
      rb.name.toLowerCase().includes(search.toLowerCase()) ||
      rb.description.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = () => {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({
      risk_level: 'manual',
      is_active: true,
      steps: [{ name: '', command: '', timeout_sec: 30, rollback_command: '' }],
    });
    setEditorOpen(true);
  };

  const handleEdit = async (id: number) => {
    try {
      const res = await customRunbookService.get(id);
      const rb = res.data;
      setEditingId(id);
      form.setFieldsValue({
        name: rb.name,
        description: rb.description,
        trigger_keywords: rb.trigger_keywords?.join(', ') || '',
        risk_level: rb.risk_level,
        is_active: rb.is_active,
        steps: rb.steps.map((s: RunbookStep) => ({
          name: s.name,
          command: s.command,
          timeout_sec: s.timeout_sec,
          rollback_command: s.rollback_command || '',
        })),
      });
      setEditorOpen(true);
    } catch {
      message.error('获取 Runbook 详情失败');
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const keywords = values.trigger_keywords
        ? values.trigger_keywords.split(',').map((k: string) => k.trim()).filter(Boolean)
        : [];
      const data: CreateRunbookRequest = {
        name: values.name,
        description: values.description || '',
        trigger_keywords: keywords,
        risk_level: values.risk_level,
        is_active: values.is_active,
        steps: values.steps.map((s: any) => ({
          name: s.name,
          command: s.command,
          timeout_sec: s.timeout_sec || 30,
          rollback_command: s.rollback_command || null,
        })),
      };

      if (editingId) {
        await customRunbookService.update(editingId, data);
        message.success('Runbook 更新成功');
      } else {
        await customRunbookService.create(data);
        message.success('Runbook 创建成功');
      }
      setEditorOpen(false);
      fetchRunbooks();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail) {
        message.error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await customRunbookService.delete(id);
      message.success('已删除');
      fetchRunbooks();
    } catch {
      message.error('删除失败');
    }
  };

  const handleDryRun = async (id: number) => {
    setDryRunLoading(true);
    setDryRunModalOpen(true);
    try {
      const res = await customRunbookService.dryRun(id);
      setDryRunResult(res.data);
    } catch {
      message.error('Dry-run 执行失败');
      setDryRunModalOpen(false);
    } finally {
      setDryRunLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await customRunbookService.exportAll();
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'custom_runbooks.json';
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  const handleImport = async (file: File) => {
    try {
      const res = await customRunbookService.importFile(file);
      const { imported, skipped, errors } = res.data;
      message.success(`导入完成：${imported} 个成功，${skipped} 个跳过`);
      if (errors?.length) {
        Modal.warning({ title: '导入警告', content: errors.join('\n') });
      }
      fetchRunbooks();
    } catch {
      message.error('导入失败');
    }
    return false; // prevent default upload
  };

  // ── AI 生成 Runbook ──────────────────────────────────────────────────
  const handleOpenAiModal = () => {
    setAiPrompt('');
    setAiRiskLevel('confirm');
    setAiResult(null);
    setAiCode('');
    setAiModalOpen(true);
  };

  const handleAiGenerate = async () => {
    if (!aiPrompt.trim()) {
      message.warning('请描述你需要的 Runbook 场景');
      return;
    }
    setAiGenerating(true);
    setAiResult(null);
    setAiCode('');
    try {
      const res = await customRunbookService.generateWithAI({
        description: aiPrompt,
        risk_level: aiRiskLevel,
      });
      const result = res.data;
      setAiResult(result);
      if (result.success && result.runbook) {
        setAiCode(JSON.stringify(result.runbook, null, 2));
      }
    } catch {
      message.error('AI 生成请求失败');
    } finally {
      setAiGenerating(false);
    }
  };

  const handleApplyAiResult = () => {
    try {
      const runbook = JSON.parse(aiCode);
      setEditingId(null);
      form.resetFields();
      form.setFieldsValue({
        name: runbook.name || '',
        description: runbook.description || '',
        trigger_keywords: (runbook.trigger_keywords || []).join(', '),
        risk_level: runbook.risk_level || 'confirm',
        is_active: true,
        steps: (runbook.steps || []).map((s: any) => ({
          name: s.name || '',
          command: s.command || '',
          timeout_sec: s.timeout_sec || 30,
          rollback_command: s.rollback_command || '',
        })),
      });
      setAiModalOpen(false);
      setEditorOpen(true);
      message.success('已应用 AI 生成结果到编辑器，请检查后保存');
    } catch {
      message.error('JSON 格式错误，请检查编辑器中的内容');
    }
  };

  const handleEditorMount = (editor: any) => {
    editorRef.current = editor;
  };

  const columns: ColumnsType<RunbookListItem> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          {record.source === 'builtin' ? (
            <BookOutlined style={{ color: '#1677ff' }} />
          ) : (
            <ThunderboltOutlined style={{ color: '#52c41a' }} />
          )}
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (source: string) =>
        source === 'builtin' ? (
          <Tag color="blue">内置</Tag>
        ) : (
          <Tag color="green">自定义</Tag>
        ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '风险级别',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 120,
      render: (level: string) => (
        <Tag color={riskLevelColors[level] || 'default'}>
          {riskLevelLabels[level] || level}
        </Tag>
      ),
    },
    {
      title: '步骤数',
      dataIndex: 'steps_count',
      key: 'steps_count',
      width: 80,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) =>
        active ? <Badge status="success" text="启用" /> : <Badge status="default" text="禁用" />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => {
        if (record.source === 'builtin') {
          return <Text type="secondary">内置（不可编辑）</Text>;
        }
        return (
          <Space size="small">
            <Tooltip title="编辑">
              <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record.id!)} />
            </Tooltip>
            <Tooltip title="Dry-Run">
              <Button size="small" icon={<ExperimentOutlined />} onClick={() => handleDryRun(record.id!)} />
            </Tooltip>
            <Popconfirm title="确认删除此 Runbook？" onConfirm={() => handleDelete(record.id!)}>
              <Tooltip title="删除">
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: 0 }}>
      <Card
        title={
          <Space>
            <SafetyOutlined />
            <span>Runbook 管理</span>
          </Space>
        }
        extra={
          <Space>
            <Input
              placeholder="搜索 Runbook..."
              prefix={<SearchOutlined />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出
            </Button>
            <Upload
              accept=".json"
              showUploadList={false}
              beforeUpload={(file) => {
                handleImport(file);
                return false;
              }}
            >
              <Button icon={<UploadOutlined />}>导入</Button>
            </Upload>
            <Button
              icon={<RobotOutlined />}
              onClick={handleOpenAiModal}
              style={{ borderColor: '#722ed1', color: '#722ed1' }}
            >
              AI 生成
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建 Runbook
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filtered}
          rowKey={(r) => r.name}
          loading={loading}
          pagination={{ pageSize: 20 }}
          size="middle"
        />
      </Card>

      {/* Runbook 编辑器 Drawer */}
      <Drawer
        title={editingId ? '编辑 Runbook' : '新建 Runbook'}
        width={720}
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        extra={
          <Space>
            <Button onClick={() => setEditorOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSave}>
              保存
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例: nginx_config_reload" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="描述此 Runbook 的用途" />
          </Form.Item>
          <Form.Item name="trigger_keywords" label="触发关键词" tooltip="逗号分隔，用于AI匹配告警">
            <Input placeholder="nginx, config, reload, 502" />
          </Form.Item>
          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="risk_level" label="风险级别" style={{ width: 200 }}>
              <Select>
                <Select.Option value="auto">自动执行</Select.Option>
                <Select.Option value="confirm">需确认</Select.Option>
                <Select.Option value="manual">手动触发</Select.Option>
                <Select.Option value="block">禁止执行</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="is_active" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
          <Divider>执行步骤</Divider>
          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Card
                    key={key}
                    size="small"
                    title={`步骤 ${name + 1}`}
                    extra={
                      fields.length > 1 ? (
                        <Button size="small" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
                      ) : null
                    }
                    style={{ marginBottom: 12 }}
                  >
                    <Form.Item
                      {...restField}
                      name={[name, 'name']}
                      label="步骤名称"
                      rules={[{ required: true, message: '请输入步骤名称' }]}
                    >
                      <Input placeholder="例: 检测 Nginx 配置" />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[name, 'command']}
                      label="执行命令"
                      rules={[{ required: true, message: '请输入命令' }]}
                    >
                      <Input.TextArea rows={2} placeholder="例: nginx -t" style={{ fontFamily: 'monospace' }} />
                    </Form.Item>
                    <Space style={{ width: '100%' }}>
                      <Form.Item {...restField} name={[name, 'timeout_sec']} label="超时(秒)" style={{ width: 120 }}>
                        <InputNumber min={1} max={3600} />
                      </Form.Item>
                    </Space>
                    <Form.Item {...restField} name={[name, 'rollback_command']} label="回滚命令 (可选)">
                      <Input placeholder="例: nginx -s reload" style={{ fontFamily: 'monospace' }} />
                    </Form.Item>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add({ name: '', command: '', timeout_sec: 30, rollback_command: '' })} block icon={<PlusOutlined />}>
                  添加步骤
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>

      {/* AI 生成 Runbook Modal */}
      <Modal
        title={
          <Space>
            <RobotOutlined style={{ color: '#722ed1' }} />
            <span>AI Runbook 生成器</span>
          </Space>
        }
        open={aiModalOpen}
        onCancel={() => setAiModalOpen(false)}
        width={1100}
        footer={null}
        destroyOnClose
        styles={{ body: { padding: '16px 24px' } }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* 输入区域 */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: 6, fontWeight: 500, color: '#333' }}>
                <RobotOutlined style={{ marginRight: 6, color: '#722ed1' }} />
                描述你的运维场景
              </div>
              <TextArea
                rows={2}
                placeholder="例：当 Redis 容器宕机时，检查 Docker 容器状态并重启 Redis，验证服务恢复"
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                disabled={aiGenerating}
                onPressEnter={(e) => { if (e.ctrlKey || e.metaKey) handleAiGenerate(); }}
                style={{ resize: 'none' }}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Select
                value={aiRiskLevel}
                onChange={setAiRiskLevel}
                style={{ width: 130 }}
                disabled={aiGenerating}
              >
                <Select.Option value="auto">自动执行</Select.Option>
                <Select.Option value="confirm">需确认</Select.Option>
                <Select.Option value="manual">手动触发</Select.Option>
                <Select.Option value="block">禁止执行</Select.Option>
              </Select>
              <Button
                type="primary"
                icon={<RobotOutlined />}
                onClick={handleAiGenerate}
                loading={aiGenerating}
                style={{ background: '#722ed1', borderColor: '#722ed1', height: 36 }}
              >
                {aiGenerating ? '生成中...' : 'AI 生成'}
              </Button>
            </div>
          </div>

          {/* 生成中 */}
          {aiGenerating && (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
              <div style={{ marginTop: 16, color: '#888', fontSize: 14 }}>AI 正在分析场景并生成 Runbook...</div>
            </div>
          )}

          {/* 生成失败 */}
          {aiResult && !aiGenerating && !aiResult.success && (
            <Alert type="error" message="生成失败" description={aiResult.error} showIcon />
          )}

          {/* 生成成功 - 双面板预览 */}
          {aiResult?.success && !aiGenerating && (() => {
            let parsed: any = {};
            try { parsed = JSON.parse(aiCode); } catch { parsed = aiResult.runbook || {}; }
            const steps = parsed.steps || [];
            const keywords = parsed.trigger_keywords || [];

            return (
              <>
                {/* 安全警告 */}
                {aiResult.safety_warnings && aiResult.safety_warnings.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    icon={<WarningOutlined />}
                    message={`${aiResult.safety_warnings.length} 条安全提示`}
                    description={
                      <ul style={{ margin: '4px 0 0', paddingLeft: 20, fontSize: 12 }}>
                        {aiResult.safety_warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    }
                    style={{ borderRadius: 8 }}
                  />
                )}

                <Tabs
                  defaultActiveKey="preview"
                  type="card"
                  items={[
                    {
                      key: 'preview',
                      label: <span><EyeOutlined /> 可视化预览</span>,
                      children: (
                        <div style={{ maxHeight: 480, overflow: 'auto', padding: '4px 0' }}>
                          {/* 基本信息 */}
                          <Card size="small" style={{ marginBottom: 12, background: '#fafafa', borderRadius: 8 }}>
                            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                              <div style={{ flex: 1, minWidth: 200 }}>
                                <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>Runbook 名称</div>
                                <div style={{ fontSize: 16, fontWeight: 600, fontFamily: 'monospace', color: '#1a1a1a' }}>
                                  {parsed.name || '-'}
                                </div>
                              </div>
                              <div>
                                <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>风险级别</div>
                                <Tag color={riskLevelColors[parsed.risk_level] || 'default'} style={{ fontSize: 13, padding: '2px 12px' }}>
                                  {riskLevelLabels[parsed.risk_level] || parsed.risk_level}
                                </Tag>
                              </div>
                              <div>
                                <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>步骤数</div>
                                <span style={{ fontSize: 16, fontWeight: 600, color: '#722ed1' }}>{steps.length}</span>
                              </div>
                            </div>
                            {parsed.description && (
                              <div style={{ marginTop: 8, color: '#555', fontSize: 13 }}>
                                {parsed.description}
                              </div>
                            )}
                            {keywords.length > 0 && (
                              <div style={{ marginTop: 8 }}>
                                <TagsOutlined style={{ color: '#999', marginRight: 6, fontSize: 12 }} />
                                {keywords.map((k: string, i: number) => (
                                  <Tag key={i} style={{ marginBottom: 2, fontSize: 11 }}>{k}</Tag>
                                ))}
                              </div>
                            )}
                          </Card>

                          {/* 步骤时间线 */}
                          <div style={{ padding: '0 4px' }}>
                            {steps.map((step: any, idx: number) => (
                              <div
                                key={idx}
                                style={{
                                  display: 'flex',
                                  gap: 12,
                                  marginBottom: 12,
                                  padding: 12,
                                  background: '#fff',
                                  border: '1px solid #f0f0f0',
                                  borderRadius: 8,
                                  borderLeft: `3px solid ${idx === steps.length - 1 ? '#52c41a' : '#722ed1'}`,
                                }}
                              >
                                <div style={{
                                  width: 28, height: 28, borderRadius: '50%',
                                  background: idx === steps.length - 1 ? '#f6ffed' : '#f9f0ff',
                                  color: idx === steps.length - 1 ? '#52c41a' : '#722ed1',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  fontWeight: 700, fontSize: 13, flexShrink: 0,
                                }}>
                                  {idx === steps.length - 1 ? <CheckCircleOutlined /> : idx + 1}
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4, color: '#1a1a1a' }}>
                                    {step.name || `步骤 ${idx + 1}`}
                                  </div>
                                  <pre style={{
                                    background: '#1e1e1e', color: '#d4d4d4', padding: '8px 12px',
                                    borderRadius: 6, fontSize: 12, margin: 0,
                                    whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                                    fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                                    lineHeight: 1.6,
                                  }}>
                                    <span style={{ color: '#6A9955' }}>$</span> {step.command}
                                  </pre>
                                  <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 12, color: '#999' }}>
                                    <span><ClockCircleOutlined style={{ marginRight: 4 }} />超时 {step.timeout_sec || 30}s</span>
                                    {step.rollback_command && (
                                      <Tooltip title={step.rollback_command}>
                                        <span style={{ color: '#faad14', cursor: 'pointer' }}>
                                          <UndoOutlined style={{ marginRight: 4 }} />有回滚命令
                                        </span>
                                      </Tooltip>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ),
                    },
                    {
                      key: 'json',
                      label: <span><CodeOutlined /> JSON 编辑</span>,
                      children: (
                        <div>
                          <div style={{
                            display: 'flex', justifyContent: 'flex-end',
                            marginBottom: 8, gap: 8,
                          }}>
                            <Tooltip title="格式化 JSON">
                              <Button
                                size="small"
                                icon={<CodeOutlined />}
                                onClick={() => {
                                  try {
                                    setAiCode(JSON.stringify(JSON.parse(aiCode), null, 2));
                                    message.success('已格式化');
                                  } catch { message.error('JSON 格式错误'); }
                                }}
                              >
                                格式化
                              </Button>
                            </Tooltip>
                            <Tooltip title="复制 JSON">
                              <Button
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => {
                                  navigator.clipboard.writeText(aiCode);
                                  message.success('已复制');
                                }}
                              />
                            </Tooltip>
                          </div>
                          <div style={{ border: '1px solid #303030', borderRadius: 8, overflow: 'hidden' }}>
                            <Editor
                              height="420px"
                              defaultLanguage="json"
                              value={aiCode}
                              onChange={(val) => setAiCode(val || '')}
                              onMount={handleEditorMount}
                              options={{
                                minimap: { enabled: false },
                                fontSize: 13,
                                lineNumbers: 'on',
                                scrollBeyondLastLine: false,
                                wordWrap: 'on',
                                formatOnPaste: true,
                                automaticLayout: true,
                                tabSize: 2,
                                padding: { top: 12 },
                                renderLineHighlight: 'gutter',
                              }}
                              theme="vs-dark"
                            />
                          </div>
                        </div>
                      ),
                    },
                  ]}
                />

                {/* 底部操作 */}
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  paddingTop: 4, borderTop: '1px solid #f0f0f0',
                }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Ctrl+Enter 快速生成 | 可在 JSON 编辑中修改后应用
                  </Text>
                  <Space>
                    <Button onClick={() => setAiModalOpen(false)}>取消</Button>
                    <Button onClick={handleAiGenerate} icon={<RobotOutlined />} disabled={aiGenerating}>
                      重新生成
                    </Button>
                    <Button
                      type="primary"
                      icon={<ThunderboltOutlined />}
                      onClick={handleApplyAiResult}
                      size="large"
                    >
                      应用到编辑器
                    </Button>
                  </Space>
                </div>
              </>
            );
          })()}

          {/* 空状态提示 */}
          {!aiResult && !aiGenerating && (
            <div style={{
              textAlign: 'center', padding: '40px 0', color: '#bbb',
              background: '#fafafa', borderRadius: 8, border: '1px dashed #e8e8e8',
            }}>
              <RobotOutlined style={{ fontSize: 40, marginBottom: 12, color: '#d9d9d9' }} />
              <div style={{ fontSize: 14 }}>输入场景描述，AI 将自动生成可执行的 Runbook</div>
              <div style={{ fontSize: 12, marginTop: 4, color: '#ccc' }}>
                支持中文描述 | 自动生成命令、关键词、回滚策略
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Dry-Run 结果 Modal */}
      <Modal
        title={
          <Space>
            <ExperimentOutlined style={{ color: '#1677ff' }} />
            <span>Dry-Run 结果</span>
          </Space>
        }
        open={dryRunModalOpen}
        onCancel={() => setDryRunModalOpen(false)}
        footer={<Button onClick={() => setDryRunModalOpen(false)}>关闭</Button>}
        width={760}
        styles={{ body: { padding: '16px 24px' } }}
      >
        {dryRunLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: '#888' }}>正在执行 Dry-Run...</div>
          </div>
        ) : dryRunResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* 概览信息 */}
            <Card size="small" style={{ background: '#fafafa', borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ flex: 1, minWidth: 160 }}>
                  <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>Runbook</div>
                  <div style={{ fontSize: 15, fontWeight: 600, fontFamily: 'monospace', color: '#1a1a1a' }}>
                    {dryRunResult.runbook_name}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>风险级别</div>
                  <Tag color={riskLevelColors[dryRunResult.risk_level]} style={{ fontSize: 13, padding: '2px 12px' }}>
                    {riskLevelLabels[dryRunResult.risk_level] || dryRunResult.risk_level}
                  </Tag>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>步骤数</div>
                  <span style={{ fontSize: 16, fontWeight: 600, color: '#1677ff' }}>{dryRunResult.total_steps}</span>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>安全检查</div>
                  {dryRunResult.all_safe ? (
                    <Tag color="success" icon={<CheckCircleOutlined />} style={{ fontSize: 13, padding: '2px 12px' }}>
                      全部通过
                    </Tag>
                  ) : (
                    <Tag color="error" icon={<WarningOutlined />} style={{ fontSize: 13, padding: '2px 12px' }}>
                      存在风险
                    </Tag>
                  )}
                </div>
              </div>
            </Card>

            {!dryRunResult.all_safe && (
              <Alert
                type="warning"
                showIcon
                message="部分命令未通过安全检查，实际执行时将被拦截"
                style={{ borderRadius: 8 }}
              />
            )}

            {/* 步骤列表 */}
            <div style={{ maxHeight: 420, overflow: 'auto' }}>
              {dryRunResult.steps.map((step, idx) => {
                const passed = step.safety_check_passed;
                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      gap: 12,
                      marginBottom: 10,
                      padding: 12,
                      background: passed ? '#fff' : '#fff2f0',
                      border: `1px solid ${passed ? '#f0f0f0' : '#ffccc7'}`,
                      borderRadius: 8,
                      borderLeft: `3px solid ${passed ? '#52c41a' : '#ff4d4f'}`,
                    }}
                  >
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: passed ? '#f6ffed' : '#fff2f0',
                      color: passed ? '#52c41a' : '#ff4d4f',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: 700, fontSize: 13, flexShrink: 0,
                    }}>
                      {passed ? <CheckCircleOutlined /> : <WarningOutlined />}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4, color: '#1a1a1a' }}>
                        步骤 {idx + 1}: {step.step_name}
                      </div>
                      <pre style={{
                        background: '#1e1e1e', color: '#d4d4d4', padding: '8px 12px',
                        borderRadius: 6, fontSize: 12, margin: 0,
                        whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                        fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                        lineHeight: 1.6,
                      }}>
                        <span style={{ color: '#6A9955' }}>$</span> {step.resolved_command}
                      </pre>
                      <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 12, color: '#999', flexWrap: 'wrap' }}>
                        <span><ClockCircleOutlined style={{ marginRight: 4 }} />超时 {step.timeout_sec}s</span>
                        {step.rollback_command && (
                          <Tooltip title={<pre style={{ margin: 0, fontSize: 11, whiteSpace: 'pre-wrap' }}>{step.rollback_command}</pre>}>
                            <span style={{ color: '#faad14', cursor: 'pointer' }}>
                              <UndoOutlined style={{ marginRight: 4 }} />有回滚命令
                            </span>
                          </Tooltip>
                        )}
                      </div>
                      {!passed && (
                        <div style={{
                          marginTop: 6, padding: '4px 8px', fontSize: 12,
                          background: '#fff1f0', border: '1px solid #ffa39e',
                          borderRadius: 4, color: '#cf1322',
                        }}>
                          <WarningOutlined style={{ marginRight: 4 }} />
                          {step.safety_message}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <Empty description="无结果" />
        )}
      </Modal>
    </div>
  );
}
