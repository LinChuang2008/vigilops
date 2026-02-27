/**
 * 通知渠道管理页面
 * 提供通知渠道的增删改查功能，支持 Webhook、邮件、钉钉、飞书、企业微信 五种渠道类型。
 */
import { useEffect, useState } from 'react';
import { Table, Card, Typography, Button, Modal, Form, Input, InputNumber, Switch, Space, Select, Tag, message } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { notificationService } from '../services/alerts';
import type { NotificationChannel } from '../services/alerts';

const { TextArea } = Input;

/** 渠道类型选项 */
const CHANNEL_TYPE_OPTIONS = [
  { value: 'webhook', label: '通用 Webhook' },
  { value: 'email', label: '邮件通知' },
  { value: 'dingtalk', label: '钉钉机器人' },
  { value: 'feishu', label: '飞书机器人' },
  { value: 'wecom', label: '企业微信机器人' },
];

/** 渠道类型对应的 Tag 颜色 */
const TYPE_TAG_COLOR: Record<string, string | undefined> = {
  webhook: undefined,
  email: 'blue',
  dingtalk: 'cyan',
  feishu: 'purple',
  wecom: 'green',
};

/** 渠道类型中文标签 */
const TYPE_LABEL: Record<string, string> = {
  webhook: 'Webhook',
  email: '邮件',
  dingtalk: '钉钉',
  feishu: '飞书',
  wecom: '企业微信',
};

/**
 * 根据渠道类型和表单值构建 config 对象
 */
function buildConfig(type: string, values: Record<string, unknown>): Record<string, unknown> {
  switch (type) {
    case 'webhook':
      return {
        url: values.url,
        ...(values.headers ? { headers: JSON.parse(values.headers as string) } : {}),
      };
    case 'email':
      return {
        smtp_host: values.smtp_host,
        smtp_port: values.smtp_port,
        smtp_user: values.smtp_user,
        smtp_password: values.smtp_password,
        smtp_ssl: values.smtp_ssl,
        recipients: (values.recipients as string).split('\n').filter(Boolean),
      };
    case 'dingtalk':
      return {
        webhook_url: values.webhook_url,
        ...(values.secret ? { secret: values.secret } : {}),
      };
    case 'feishu':
      return {
        webhook_url: values.webhook_url,
        ...(values.secret ? { secret: values.secret } : {}),
      };
    case 'wecom':
      return { webhook_url: values.webhook_url };
    default:
      return {};
  }
}

/**
 * 从 config 反向解析为表单字段值（用于编辑回填）
 */
function parseConfigToFields(type: string, config: Record<string, unknown>): Record<string, unknown> {
  switch (type) {
    case 'webhook':
      return {
        url: config.url,
        headers: config.headers ? JSON.stringify(config.headers, null, 2) : undefined,
      };
    case 'email':
      return {
        smtp_host: config.smtp_host,
        smtp_port: config.smtp_port,
        smtp_user: config.smtp_user,
        smtp_password: config.smtp_password,
        smtp_ssl: config.smtp_ssl,
        recipients: Array.isArray(config.recipients) ? (config.recipients as string[]).join('\n') : '',
      };
    case 'dingtalk':
    case 'feishu':
      return { webhook_url: config.webhook_url, secret: config.secret };
    case 'wecom':
      return { webhook_url: config.webhook_url };
    default:
      return {};
  }
}

/**
 * 通知渠道管理组件
 */
export default function NotificationChannels() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  /** 当前编辑的渠道（null 表示新建） */
  const [editing, setEditing] = useState<NotificationChannel | null>(null);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  /** 获取通知渠道列表 */
  const fetchList = async () => {
    setLoading(true);
    try {
      const { data } = await notificationService.listChannels();
      setChannels(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchList(); }, []);

  /** 打开新建弹窗 */
  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ type: 'webhook', smtp_port: 465, smtp_ssl: true });
    setModalOpen(true);
  };

  /** 打开编辑弹窗 */
  const openEdit = (record: NotificationChannel) => {
    setEditing(record);
    const fields = parseConfigToFields(record.type, record.config);
    form.resetFields();
    form.setFieldsValue({ name: record.name, type: record.type, ...fields });
    setModalOpen(true);
  };

  /** 提交创建/编辑 */
  const handleSubmit = async (values: Record<string, unknown>) => {
    const type = values.type as string;
    try {
      if (type === 'webhook' && values.headers) {
        JSON.parse(values.headers as string);
      }
    } catch {
      messageApi.error('Headers 必须是合法的 JSON');
      return;
    }

    const config = buildConfig(type, values);
    try {
      if (editing) {
        await notificationService.updateChannel(editing.id, {
          name: values.name as string,
          type,
          config,
        });
        messageApi.success('更新成功');
      } else {
        await notificationService.createChannel({
          name: values.name as string,
          type,
          config,
          enabled: true,
        });
        messageApi.success('创建成功');
      }
      setModalOpen(false);
      form.resetFields();
      fetchList();
    } catch { messageApi.error(editing ? '更新失败' : '创建失败'); }
  };

  /** 切换渠道启用/禁用状态 */
  const handleToggle = async (record: NotificationChannel) => {
    try {
      await notificationService.updateChannel(record.id, { enabled: !record.enabled });
      messageApi.success(record.enabled ? '已禁用' : '已启用');
      fetchList();
    } catch { messageApi.error('操作失败'); }
  };

  /** 删除渠道 */
  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除此通知渠道？',
      icon: <ExclamationCircleOutlined />,
      onOk: async () => {
        try {
          await notificationService.deleteChannel(id);
          messageApi.success('已删除');
          fetchList();
        } catch { messageApi.error('删除失败'); }
      },
    });
  };

  /** 表格列定义 */
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name' },
    {
      title: '类型', dataIndex: 'type', width: 120,
      render: (t: string) => <Tag color={TYPE_TAG_COLOR[t]}>{TYPE_LABEL[t] || t}</Tag>,
    },
    {
      title: '启用', dataIndex: 'enabled', width: 80,
      render: (v: boolean, r: NotificationChannel) => (
        <Switch checked={v} onChange={() => handleToggle(r)} />
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', render: (t: string) => new Date(t).toLocaleString() },
    {
      title: '操作', key: 'action', width: 140,
      render: (_: unknown, r: NotificationChannel) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(r)}>编辑</Button>
          <Button type="link" danger size="small" onClick={() => handleDelete(r.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  /** 根据渠道类型渲染配置字段 */
  const renderConfigFields = (channelType: string) => {
    switch (channelType) {
      case 'webhook':
        return (
          <>
            <Form.Item name="url" label="Webhook URL" rules={[{ required: true, message: '请输入 URL' }, { type: 'url', message: '请输入合法 URL' }]}>
              <Input placeholder="https://example.com/webhook" />
            </Form.Item>
            <Form.Item name="headers" label="Headers（JSON，可选）">
              <TextArea rows={3} placeholder='{"Content-Type": "application/json"}' />
            </Form.Item>
          </>
        );
      case 'email':
        return (
          <>
            <Form.Item name="smtp_host" label="SMTP 服务器" rules={[{ required: true, message: '请输入 SMTP 服务器地址' }]}>
              <Input placeholder="smtp.example.com" />
            </Form.Item>
            <Form.Item name="smtp_port" label="SMTP 端口" rules={[{ required: true }]}>
              <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="smtp_user" label="SMTP 用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input placeholder="user@example.com" />
            </Form.Item>
            <Form.Item name="smtp_password" label="SMTP 密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password placeholder="密码" />
            </Form.Item>
            <Form.Item name="smtp_ssl" label="启用 SSL" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="recipients" label="收件人（每行一个邮箱）" rules={[{ required: true, message: '请输入收件人' }]}>
              <TextArea rows={3} placeholder={'admin@example.com\nops@example.com'} />
            </Form.Item>
          </>
        );
      case 'dingtalk':
        return (
          <>
            <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true, message: '请输入钉钉机器人 Webhook URL' }]}>
              <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
            </Form.Item>
            <Form.Item name="secret" label="加签密钥（可选）">
              <Input placeholder="SEC..." />
            </Form.Item>
          </>
        );
      case 'feishu':
        return (
          <>
            <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true, message: '请输入飞书机器人 Webhook URL' }]}>
              <Input placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
            </Form.Item>
            <Form.Item name="secret" label="签名校验密钥（可选）">
              <Input placeholder="密钥" />
            </Form.Item>
          </>
        );
      case 'wecom':
        return (
          <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true, message: '请输入企业微信机器人 Webhook URL' }]}>
            <Input placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          </Form.Item>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      {contextHolder}
      <Typography.Title level={4}>通知渠道</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={openCreate}>新增渠道</Button>
      </Space>
      <Card>
        <Table dataSource={channels} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>

      {/* 新建/编辑渠道弹窗 */}
      <Modal
        title={editing ? '编辑渠道' : '新增渠道'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
        width={window.innerWidth < 768 ? '100%' : 560}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{ type: 'webhook', smtp_port: 465, smtp_ssl: true }}>
          <Form.Item name="name" label="渠道名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如: 运维群通知" />
          </Form.Item>
          <Form.Item name="type" label="渠道类型" rules={[{ required: true }]}>
            <Select options={CHANNEL_TYPE_OPTIONS} disabled={!!editing} />
          </Form.Item>
          {/* 根据渠道类型动态渲染配置字段 */}
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.type !== cur.type}>
            {({ getFieldValue }) => renderConfigFields(getFieldValue('type'))}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
