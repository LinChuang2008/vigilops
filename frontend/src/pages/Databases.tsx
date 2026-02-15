import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Tag, Typography, Spin } from 'antd';
import { databaseService } from '../services/databases';
import type { DatabaseItem } from '../services/databases';

const statusColor: Record<string, string> = {
  healthy: 'success',
  warning: 'warning',
  critical: 'error',
  unknown: 'default',
};

const dbTypeIcon: Record<string, string> = {
  postgres: '🐘',
  postgresql: '🐘',
  mysql: '🐬',
};

export default function Databases() {
  const [databases, setDatabases] = useState<DatabaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await databaseService.list();
        setDatabases(data.databases || []);
      } catch { /* ignore */ } finally { setLoading(false); }
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const columns = [
    {
      title: '数据库名', dataIndex: 'name', key: 'name',
      render: (name: string, record: DatabaseItem) => (
        <span>{dbTypeIcon[record.db_type] || '🗄️'} {name}</span>
      ),
    },
    {
      title: '类型', dataIndex: 'db_type', key: 'db_type',
      render: (t: string) => t === 'postgres' || t === 'postgresql' ? 'PostgreSQL' : t === 'mysql' ? 'MySQL' : t,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '连接数', key: 'connections',
      render: (_: unknown, r: DatabaseItem) => r.latest_metrics?.connections_total ?? '-',
    },
    {
      title: '大小 (MB)', key: 'size',
      render: (_: unknown, r: DatabaseItem) => r.latest_metrics?.database_size_mb?.toFixed(1) ?? '-',
    },
    {
      title: '慢查询', key: 'slow',
      render: (_: unknown, r: DatabaseItem) => {
        const v = r.latest_metrics?.slow_queries;
        if (v == null) return '-';
        return v > 0 ? <Tag color="warning">{v}</Tag> : <Tag color="success">{v}</Tag>;
      },
    },
    {
      title: 'QPS', key: 'qps',
      render: (_: unknown, r: DatabaseItem) => r.latest_metrics?.qps?.toFixed(1) ?? '-',
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>数据库监控</Typography.Title>
      <Table
        dataSource={databases}
        columns={columns}
        rowKey="id"
        size="small"
        pagination={false}
        onRow={(record) => ({ onClick: () => navigate(`/databases/${record.id}`), style: { cursor: 'pointer' } })}
      />
    </div>
  );
}
