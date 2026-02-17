/**
 * 通知模板管理页面
 * 提供通知模板的增删改查功能，支持变量预览。
 */
import { useEffect, useState } from 'react';
import { Table, Card, Typography, Button, Modal, Form, Input, Switch, Select, Tag, Space, message } from 'antd';
import { ExclamationCircleOutlined, EyeOutlined } from '@ant-design/icons';
import { notificationTemplateService } from '../services/notificationTemplates';
import type { NotificationTemplate } from '../services/notificationTemplates';

const { TextArea } = Input;

/** 渠道类型选项（含 all） */
const CHANNEL_TYPE_OPTIONS = [
  { value: 'all', label: '全部类型' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'email', label: '邮件' },
  { value: 'dingtalk', label: '钉钉' },
  { value: 'feishu', label: '飞书' },
  { value: 'wecom', label: '企业微信' },
];

/** 渠道类型 Tag 颜色映射 */
const TYPE_TAG_COLOR: Record<string, string | undefined> = {
  all: 'orange',
  webhook: undefined,
  email: 'blue',
  dingtalk: 'cyan',
  feishu: 'purple',
  wecom: 'green',
};

/** 渠道类型中文名 */
const TYPE_LABEL: Record<string, string> = {
  all: '全部',
  webhook: 'Webhook',
  email: '邮件',
  dingtalk: '钉钉',
  feishu: '飞书',
  wecom: '企业微信',
};

/** 可用模板变量 */
const AVAILABLE_VARS = ['{title}', '{severity}', '{message}', '{metric_value}', '{threshold}', '{host_id}', '{fired_at}', '{resolved_at}'];

/** 预览用示例数据 */
const SAMPLE_DATA: Record<string, string> = {
  '{title}': 'CPU 使用率过高',
  '{severity}': 'critical',
  '{message}': '主机 web-01 CPU 使用率达到 95%',
  '{metric_value}': '95.2',
  '{threshold}': '90',
  '{host_id}': 'web-01',
  '{fired_at}': '2026-02-17 11:30:00',
  '{resolved_at}': '2026-02-17 11:45:00',
};

/** 用示例数据替换模板中的变量 */
function renderPreview(template: string): string {
  let result = template;
  for (const [k, v] of Object.entries(SAMPLE_DATA)) {
    result = result.replaceAll(k, v);
  }
  return result;
}

/**
 * 通知模板管理组件
 */
export default function NotificationTemplates() {
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<NotificationTemplate | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState<{ subject?: string; body: string }>({ body: '' });
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  /** 获取模板列表 */
  const fetchList = async () => {
    setLoading(true);
    try {
      const { data } = await notificationTemplateService.fetchTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchList(); }, []);

  /** 打开新建弹窗 */
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ channel_type: 'all', is_default: false });
    setModalOpen(true);
  };

  /** 打开编辑弹窗 */
  const openEdit = (record: NotificationTemplate) => {
    setEditing(record);
    form.resetFields();
    form.setFieldsValue({
      name: record.name,
      channel_type: record.channel_type,
      subject_template: record.subject_template,
      body_template: record.body_template,
      is_default: record.is_default,
    });
    setModalOpen(true);
  };

  /** 提交创建/编辑 */
  const handleSubmit = async (values: Record<string, unknown>) => {
    const payload = {
      name: values.name as string,
      channel_type: values.channel_type as string,
      subject_template: values.subject_template as string | null || null,
      body_template: values.body_template as string,
      is_default: values.is_default as boolean,
    };
    try {
      if (editing) {
        await notificationTemplateService.updateTemplate(editing.id, payload);
        messageApi.success('更新成功');
      } else {
        await notificationTemplateService.createTemplate(payload);
        messageApi.success('创建成功');
      }
      setModalOpen(false);
      fetchList();
    } catch { messageApi.error(editing ? '更新失败' : '创建失败'); }
  };

  /** 删除模板 */
  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除此通知模板？',
      icon: <ExclamationCircleOutlined />,
      onOk: async () => {
        try {
          await notificationTemplateService.deleteTemplate(id);
          messageApi.success('已删除');
          fetchList();
        } catch { messageApi.error('删除失败'); }
      },
    });
  };

  /** 预览模板 */
  const handlePreview = (record: NotificationTemplate) => {
    setPreviewContent({
      subject: record.subject_template ? renderPreview(record.subject_template) : undefined,
      body: renderPreview(record.body_template),
    });
    setPreviewOpen(true);
  };

  /** 切换默认状态 */
  const handleToggleDefault = async (record: NotificationTemplate) => {
    try {
      await notificationTemplateService.updateTemplate(record.id, { is_default: !record.is_default });
      messageApi.success('已更新');
      fetchList();
    } catch { messageApi.error('操作失败'); }
  };

  /** 表格列定义 */
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name' },
    {
      title: '渠道类型', dataIndex: 'channel_type', width: 120,
      render: (t: string) => <Tag color={TYPE_TAG_COLOR[t]}>{TYPE_LABEL[t] || t}</Tag>,
    },
    {
      title: '默认', dataIndex: 'is_default', width: 80,
      render: (v: boolean, r: NotificationTemplate) => (
        <Switch checked={v} onChange={() => handleToggleDefault(r)} size="small" />
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', render: (t: string) => new Date(t).toLocaleString() },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: unknown, r: NotificationTemplate) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handlePreview(r)}>预览</Button>
          <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
          <Button type="link" danger size="small" onClick={() => handleDelete(r.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {contextHolder}
      <Typography.Title level={4}>通知模板</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={openCreate}>新增模板</Button>
      </Space>
      <Card>
        <Table dataSource={templates} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>

      {/* 新建/编辑模板弹窗 */}
      <Modal
        title={editing ? '编辑模板' : '新增模板'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ channel_type: 'all', is_default: false }}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input placeholder="例如: 默认告警模板" />
          </Form.Item>
          <Form.Item name="channel_type" label="渠道类型" rules={[{ required: true }]}>
            <Select options={CHANNEL_TYPE_OPTIONS} />
          </Form.Item>
          {/* 标题模板：仅 email 或 all 时显示 */}
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.channel_type !== cur.channel_type}>
            {({ getFieldValue }) => {
              const ct = getFieldValue('channel_type');
              return (ct === 'email' || ct === 'all') ? (
                <Form.Item name="subject_template" label="标题模板">
                  <Input placeholder="[{severity}] {title}" />
                </Form.Item>
              ) : null;
            }}
          </Form.Item>
          <Form.Item name="body_template" label="消息体模板" rules={[{ required: true, message: '请输入消息体模板' }]}>
            <TextArea rows={6} placeholder={'告警: {title}\n级别: {severity}\n详情: {message}\n指标值: {metric_value}\n阈值: {threshold}\n主机: {host_id}\n触发时间: {fired_at}'} />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认" valuePropName="checked">
            <Switch />
          </Form.Item>
          <div style={{ background: '#f5f5f5', padding: '8px 12px', borderRadius: 6, fontSize: 12, color: '#666' }}>
            可用变量：{AVAILABLE_VARS.map(v => <Tag key={v} style={{ marginBottom: 4 }}>{v}</Tag>)}
          </div>
        </Form>
      </Modal>

      {/* 预览弹窗 */}
      <Modal title="模板预览" open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={500}>
        {previewContent.subject && (
          <div style={{ marginBottom: 12 }}>
            <Typography.Text strong>标题：</Typography.Text>
            <div style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4 }}>{previewContent.subject}</div>
          </div>
        )}
        <div>
          <Typography.Text strong>消息体：</Typography.Text>
          <div style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4, whiteSpace: 'pre-wrap' }}>{previewContent.body}</div>
        </div>
      </Modal>
    </div>
  );
}
