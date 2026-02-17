/**
 * 通知渠道管理页面
 * 提供通知渠道的增删改查功能，支持创建 Webhook 类型渠道、启用/禁用切换和删除操作。
 */
import { useEffect, useState } from 'react';
import { Table, Card, Typography, Button, Modal, Form, Input, Switch, Space, message } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { notificationService } from '../services/alerts';
import type { NotificationChannel } from '../services/alerts';

/**
 * 通知渠道管理组件
 * 以表格展示已配置的通知渠道，支持新增 Webhook 渠道、启用/禁用和删除
 */
export default function NotificationChannels() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(false);
  /** 新增渠道弹窗是否打开 */
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  /** 获取通知渠道列表 */
  const fetch = async () => {
    setLoading(true);
    try {
      const { data } = await notificationService.listChannels();
      setChannels(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  /** 创建新的 Webhook 渠道 */
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

  /** 切换渠道的启用/禁用状态 */
  const handleToggle = async (record: NotificationChannel) => {
    try {
      await notificationService.updateChannel(record.id, { enabled: !record.enabled });
      messageApi.success(record.enabled ? '已禁用' : '已启用');
      fetch();
    } catch { messageApi.error('操作失败'); }
  };

  /** 删除渠道（带确认弹窗） */
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

  /** 表格列定义 */
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

      {/* 新增 Webhook 渠道弹窗 */}
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
