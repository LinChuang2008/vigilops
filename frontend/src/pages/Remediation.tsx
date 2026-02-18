/**
 * 自动修复列表页
 * 展示所有修复任务，支持按状态、主机筛选和分页
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Card, Typography, Select, Space, Button, Row, Col } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { remediationService } from '../services/remediation';
import type { Remediation } from '../services/remediation';
import { RemediationStatusTag, RiskLevelTag } from '../components/RemediationBadge';

export default function RemediationList() {
  const navigate = useNavigate();
  const [data, setData] = useState<Remediation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [hostFilter, setHostFilter] = useState<string>('');
  /** 从已有数据中提取主机列表用于筛选 */
  const [hosts, setHosts] = useState<string[]>([]);

  const fetch = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 20 };
      if (statusFilter) params.status = statusFilter;
      if (hostFilter) params.host = hostFilter;
      const { data: res } = await remediationService.list(params);
      setData(res.items || []);
      setTotal(res.total || 0);
      // 收集唯一主机名
      const allHosts = (res.items || []).map((r) => r.host).filter(Boolean);
      setHosts((prev) => [...new Set([...prev, ...allHosts])]);
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [page, statusFilter, hostFilter]);

  const columns = [
    {
      title: '时间', dataIndex: 'created_at', width: 180,
      render: (t: string) => new Date(t).toLocaleString(),
    },
    { title: '告警名', dataIndex: 'alert_name', ellipsis: true },
    { title: '主机', dataIndex: 'host', width: 160 },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (s: string) => <RemediationStatusTag status={s} />,
    },
    { title: 'Runbook', dataIndex: 'runbook', ellipsis: true },
    {
      title: '风险级别', dataIndex: 'risk_level', width: 100,
      render: (l: string) => <RiskLevelTag level={l} />,
    },
    {
      title: '操作', key: 'action', width: 80,
      render: (_: unknown, record: Remediation) => (
        <Button type="link" size="small" onClick={() => navigate(`/remediations/${record.id}`)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>
        <ThunderboltOutlined style={{ marginRight: 8 }} />
        自动修复
      </Typography.Title>

      <Row style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Select
              placeholder="状态" allowClear style={{ width: 130 }}
              onChange={(v) => { setStatusFilter(v || ''); setPage(1); }}
              options={[
                { label: '待审批', value: 'pending' },
                { label: '已审批', value: 'approved' },
                { label: '执行中', value: 'executing' },
                { label: '已完成', value: 'success' },
                { label: '失败', value: 'failed' },
                { label: '已拒绝', value: 'rejected' },
              ]}
            />
            <Select
              placeholder="主机" allowClear style={{ width: 180 }}
              showSearch
              onChange={(v) => { setHostFilter(v || ''); setPage(1); }}
              options={hosts.map((h) => ({ label: h, value: h }))}
            />
          </Space>
        </Col>
      </Row>

      <Card>
        <Table
          dataSource={data} columns={columns} rowKey="id" loading={loading}
          pagination={{ current: page, pageSize: 20, total, onChange: (p) => setPage(p) }}
        />
      </Card>
    </div>
  );
}
