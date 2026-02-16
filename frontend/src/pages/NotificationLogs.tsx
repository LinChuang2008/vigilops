import { useEffect, useState } from 'react';
import { Table, Card, Typography, Tag, InputNumber, Space } from 'antd';
import { notificationService } from '../services/alerts';
import type { NotificationLog } from '../services/alerts';

export default function NotificationLogs() {
  const [logs, setLogs] = useState<NotificationLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(50);

  const fetch = async () => {
    setLoading(true);
    try {
      const { data } = await notificationService.listLogs({ limit });
      setLogs(Array.isArray(data) ? data : []);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [limit]);

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
