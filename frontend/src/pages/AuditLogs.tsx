/**
 * 审计日志页面
 *
 * 展示系统操作审计记录，支持按操作类型和用户筛选，分页浏览。
 * 操作类型通过不同颜色 Tag 区分，JSON 格式详情支持 Tooltip 展示。
 */
import { useEffect, useState } from 'react';
import { Table, Tag, Select, Row, Col, Typography, Space, Tooltip, message } from 'antd';
import dayjs from 'dayjs';
import type { AuditLog } from '../services/users';
import { fetchAuditLogs, fetchUsers } from '../services/users';

const { Title } = Typography;

/** 操作类型颜色映射 */
const actionColorMap: Record<string, string> = {
  create: 'green',
  update: 'blue',
  delete: 'red',
  login: 'cyan',
  logout: 'default',
  reset_password: 'orange',
  enable: 'green',
  disable: 'volcano',
};

/** 尝试格式化 JSON 字符串 */
function formatDetail(detail: string | null): string {
  if (!detail) return '-';
  try {
    return JSON.stringify(JSON.parse(detail), null, 2);
  } catch {
    return detail;
  }
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [userFilter, setUserFilter] = useState<number | undefined>();
  const [userOptions, setUserOptions] = useState<{ label: string; value: number }[]>([]);
  const [messageApi, contextHolder] = message.useMessage();

  /** 加载审计日志 */
  const load = async () => {
    setLoading(true);
    try {
      const { data } = await fetchAuditLogs({
        page,
        page_size: pageSize,
        action: actionFilter,
        user_id: userFilter,
      });
      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch {
      messageApi.error('获取审计日志失败');
    } finally {
      setLoading(false);
    }
  };

  /** 加载用户列表用于筛选下拉 */
  const loadUsers = async () => {
    try {
      const { data } = await fetchUsers(1, 100);
      setUserOptions((data.items || []).map((u) => ({ label: u.name || u.email, value: u.id })));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => { loadUsers(); }, []);
  useEffect(() => { load(); }, [page, actionFilter, userFilter]);

  /** 操作类型选项 */
  const actionOptions = [
    { label: '创建', value: 'create' },
    { label: '更新', value: 'update' },
    { label: '删除', value: 'delete' },
    { label: '登录', value: 'login' },
    { label: '登出', value: 'logout' },
    { label: '重置密码', value: 'reset_password' },
    { label: '启用', value: 'enable' },
    { label: '禁用', value: 'disable' },
  ];

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss'),
    },
    { title: '用户', dataIndex: 'user_name', key: 'user_name', width: 120 },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action: string) => (
        <Tag color={actionColorMap[action] || 'default'}>{action}</Tag>
      ),
    },
    { title: '资源类型', dataIndex: 'resource_type', key: 'resource_type', width: 120 },
    { title: '资源ID', dataIndex: 'resource_id', key: 'resource_id', width: 80, render: (v: number | null) => v ?? '-' },
    { title: 'IP 地址', dataIndex: 'ip_address', key: 'ip_address', width: 140, render: (v: string | null) => v ?? '-' },
    {
      title: '详情',
      dataIndex: 'detail',
      key: 'detail',
      ellipsis: true,
      render: (detail: string | null) => {
        const text = formatDetail(detail);
        if (text === '-') return '-';
        return (
          <Tooltip title={<pre style={{ margin: 0, maxHeight: 300, overflow: 'auto', fontSize: 12 }}>{text}</pre>}>
            <span style={{ cursor: 'pointer' }}>{detail && detail.length > 50 ? detail.slice(0, 50) + '...' : detail}</span>
          </Tooltip>
        );
      },
    },
  ];

  return (
    <>
      {contextHolder}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Title level={4} style={{ margin: 0 }}>审计日志</Title></Col>
        <Col>
          <Space>
            <Select
              allowClear
              placeholder="操作类型"
              style={{ width: 140 }}
              options={actionOptions}
              value={actionFilter}
              onChange={(v) => { setActionFilter(v); setPage(1); }}
            />
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="用户筛选"
              style={{ width: 160 }}
              options={userOptions}
              value={userFilter}
              onChange={(v) => { setUserFilter(v); setPage(1); }}
            />
          </Space>
        </Col>
      </Row>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={logs}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 条`,
        }}
      />
    </>
  );
}
