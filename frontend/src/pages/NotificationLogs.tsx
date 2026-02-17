/**
 * 通知日志页面
 * 展示告警通知的发送记录，包括发送时间、关联的告警规则、渠道、状态和消息内容，
 * 支持自定义显示条数。
 */
import { useEffect, useState } from 'react';
import { Table, Card, Typography, Tag, InputNumber, Space } from 'antd';
import { notificationService } from '../services/alerts';
import type { NotificationLog } from '../services/alerts';

/**
 * 通知日志组件
 * 以表格形式展示通知发送历史记录，支持调整显示条数
 */
export default function NotificationLogs() {
  const [logs, setLogs] = useState<NotificationLog[]>([]);
  const [loading, setLoading] = useState(false);
  /** 显示条数限制，默认 50 条 */
  const [limit, setLimit] = useState(50);

  /** 根据 limit 获取通知日志 */
  const fetch = async () => {
    setLoading(true);
    try {
      const { data } = await notificationService.listLogs({ limit });
      setLogs(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  // limit 变化时重新获取
  useEffect(() => { fetch(); }, [limit]);

  /** 表格列定义 */
  const columns = [
    { title: '时间', dataIndex: 'sent_at', render: (t: string) => t ? new Date(t).toLocaleString() : '-' },
    { title: '告警规则 ID', dataIndex: 'alert_rule_id', render: (v: number | null) => v ?? '-' },
    { title: '渠道 ID', dataIndex: 'channel_id', render: (v: number | null) => v ?? '-' },
    {
      title: '状态', dataIndex: 'status',
      render: (s: string) => <Tag color={s === 'success' ? 'green' : s === 'failed' ? 'red' : 'default'}>{s}</Tag>,
    },
    { title: '消息', dataIndex: 'message', ellipsis: true },
  ];

  return (
    <div>
      <Typography.Title level={4}>通知日志</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <span>显示条数：</span>
        <InputNumber min={1} max={200} value={limit} onChange={v => v && setLimit(v)} />
      </Space>
      <Card>
        <Table dataSource={logs} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>
    </div>
  );
}
