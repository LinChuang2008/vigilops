/**
 * Runbook 管理页面
 * 列表视图展示所有 Runbook（内置 + 自定义），支持创建、编辑、删除、dry-run
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Card, Table, Button, Tag, Space, Modal, message, Upload, Tooltip,
  Typography, Input, Badge, Popconfirm, Drawer, Form, Select, Switch,
  InputNumber, Divider, Alert, Collapse, Descriptions, Empty,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, EditOutlined,
  DownloadOutlined, UploadOutlined, BookOutlined, SafetyOutlined,
  ThunderboltOutlined, ExperimentOutlined, SearchOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  customRunbookService,
} from '../services/customRunbook';
import type {
  RunbookListItem,
  RunbookStep,
  CreateRunbookRequest,
  DryRunResponse,
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

      {/* Dry-Run 结果 Modal */}
      <Modal
        title={
          <Space>
            <ExperimentOutlined />
            <span>Dry-Run 结果</span>
          </Space>
        }
        open={dryRunModalOpen}
        onCancel={() => setDryRunModalOpen(false)}
        footer={<Button onClick={() => setDryRunModalOpen(false)}>关闭</Button>}
        width={700}
      >
        {dryRunLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : dryRunResult ? (
          <>
            <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Runbook">{dryRunResult.runbook_name}</Descriptions.Item>
              <Descriptions.Item label="风险级别">
                <Tag color={riskLevelColors[dryRunResult.risk_level]}>
                  {riskLevelLabels[dryRunResult.risk_level] || dryRunResult.risk_level}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="总步骤">{dryRunResult.total_steps}</Descriptions.Item>
              <Descriptions.Item label="安全检查">
                {dryRunResult.all_safe ? (
                  <Tag color="green">全部通过</Tag>
                ) : (
                  <Tag color="red">存在风险</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
            {!dryRunResult.all_safe && (
              <Alert
                type="warning"
                message="部分命令未通过安全检查，实际执行时将被拦截"
                style={{ marginBottom: 16 }}
              />
            )}
            <Collapse
              defaultActiveKey={dryRunResult.steps.map((_, i) => String(i))}
              items={dryRunResult.steps.map((step, i) => ({
                key: String(i),
                label: (
                  <Space>
                    {step.safety_check_passed ? (
                      <Badge status="success" />
                    ) : (
                      <Badge status="error" />
                    )}
                    <span>步骤 {i + 1}: {step.step_name}</span>
                  </Space>
                ),
                children: (
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      <Text type="secondary">将执行命令：</Text>
                      <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, margin: '4px 0' }}>
                        {step.resolved_command}
                      </pre>
                    </div>
                    <Text type="secondary">超时：{step.timeout_sec}秒</Text>
                    {step.rollback_command && (
                      <div style={{ marginTop: 8 }}>
                        <Text type="secondary">回滚命令：</Text>
                        <pre style={{ background: '#fff7e6', padding: 8, borderRadius: 4, margin: '4px 0' }}>
                          {step.rollback_command}
                        </pre>
                      </div>
                    )}
                    {!step.safety_check_passed && (
                      <Alert type="error" message={step.safety_message} style={{ marginTop: 8 }} />
                    )}
                  </div>
                ),
              }))}
            />
          </>
        ) : (
          <Empty description="无结果" />
        )}
      </Modal>
    </div>
  );
}
