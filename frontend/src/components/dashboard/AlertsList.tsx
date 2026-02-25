/**
 * 最新告警列表组件
 * 显示最新的告警信息
 */
import { Card, Table, Tag } from 'antd';

interface AlertItem {
  id: string;
  title: string;
  severity: string;
  status: string;
  fired_at: string;
}

interface AlertsListProps {
  alerts: AlertItem[];
}

export default function AlertsList({ alerts }: AlertsListProps) {
  const severityColor: Record<string, string> = { 
    critical: 'red', 
    warning: 'orange', 
    info: 'blue' 
  };

  const columns = [
    { 
      title: '标题', 
      dataIndex: 'title', 
      key: 'title' 
    },
    { 
      title: '严重级别', 
      dataIndex: 'severity', 
      key: 'severity',
      render: (severity: string) => (
        <Tag color={severityColor[severity] || 'default'}>
          {severity}
        </Tag>
      )
    },
    { 
      title: '触发时间', 
      dataIndex: 'fired_at', 
      key: 'fired_at',
      render: (time: string) => new Date(time).toLocaleString()
    },
  ];

  return (
    <Card title="最新告警">
      <Table
        dataSource={alerts}
        rowKey="id"
        columns={columns}
        pagination={false}
        size="small"
        locale={{ emptyText: '暂无活跃告警' }}
      />
    </Card>
  );
}