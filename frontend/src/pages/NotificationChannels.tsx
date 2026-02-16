import { useEffect, useState } from 'react';
import { Table, Card, Typography, Button, Modal, Form, Input, Switch, Space, message } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { notificationService } from '../services/alerts';
import type { NotificationChannel } from '../services/alerts';

export default function NotificationChannels() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  const fetch = async () => {
    setLoading(true);
    try {
      const { data } = await notificationService.listChannels();
      setChannels(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const handleCreate = async (values: { name: string; webhook_url: string }) => {
    try {
      await notificationService.createChannel({
        name: values.name,
        type: 'webhook',
        config: { url: values.webhook_url },
        enabled: true,
      });
      messageApi.success('创建成功');
      setModalOpen(false);
      form.resetFields();
      fetch();
    } catch { messageApi.error('创建失败'); }
  };

  const handleToggle = async (record: NotificationChannel) => {
    try {
      await notificationService.updateChannel(record.id, { enabled: !record.enabled });
      messageApi.success(record.enabled ? '已禁用' : '已启用');
      fetch();
    } catch { messageApi.error('操作失败'); }
  };

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: '确认删除此通知渠道？',
      icon: <ExclamationCircleOutlined />,
      onOk: async () => {
        try {
          await notificationService.deleteChannel(id);
          messageApi.success('已删除');
          fetch();
        } catch { messageApi.error('删除失败'); }
      },
    });
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'type' },
    {
      title: 'Webhook URL', key: 'url',
      render: (_: unknown, r: NotificationChannel) => {
        const url = (r.config as Record<string, unknown>)?.url;
        return typeof url === 'string' ? url : '-';
      },
    },
    {
      title: '启用', dataIndex: 'enabled',
      render: (v: boolean, r: NotificationChannel) => (
        <Switch checked={v} onChange={() => handleToggle(r)} />
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', render: (t: string) => new Date(t).toLocaleString() },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: NotificationChannel) => (
        <Button type="link" danger size="small" onClick={() => handleDelete(r.id)}>删除</Button>
      ),
    },
  ];

  return (
    <div>
      {contextHolder}
      <Typography.Title level={4}>通知渠道</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => { form.resetFields(); setModalOpen(true); }}>新增 Webhook 渠道</Button>
      </Space>
      <Card>
        <Table dataSource={channels} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>
      <Modal title="新增 Webhook 渠道" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="渠道名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如: 运维群 Webhook" />
          </Form.Item>
          <Form.Item name="webhook_url" label="Webhook URL" rules={[{ required: true, message: '请输入 URL' }, { type: 'url', message: '请输入合法 URL' }]}>
            <Input placeholder="https://example.com/webhook" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
