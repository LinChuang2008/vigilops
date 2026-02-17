/**
 * 用户管理页面
 *
 * 提供用户列表展示、新建/编辑/删除用户、重置密码、启用/禁用等功能。
 * 角色通过不同颜色 Tag 区分：admin=red, operator=blue, viewer=default。
 */
import { useEffect, useState } from 'react';
import { Table, Button, Tag, Switch, Modal, Form, Input, Select, Row, Col, Typography, Space, message, Popconfirm } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { User, UserCreate, UserUpdate } from '../services/users';
import { fetchUsers, createUser, updateUser, deleteUser, resetPassword } from '../services/users';

const { Title } = Typography;

/** 角色颜色映射 */
const roleColorMap: Record<string, string> = {
  admin: 'red',
  operator: 'blue',
  viewer: 'default',
};

/** 角色选项 */
const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '操作员', value: 'operator' },
  { label: '观察者', value: 'viewer' },
];

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  /** 新建/编辑弹窗 */
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  /** 重置密码弹窗 */
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [pwdUserId, setPwdUserId] = useState<number | null>(null);
  const [pwdForm] = Form.useForm();

  const [messageApi, contextHolder] = message.useMessage();

  /** 加载用户列表 */
  const load = async () => {
    setLoading(true);
    try {
      const { data } = await fetchUsers(page, pageSize);
      setUsers(data.items || []);
      setTotal(data.total || 0);
    } catch {
      messageApi.error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page]);

  /** 打开新建弹窗 */
  const handleCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setModalOpen(true);
  };

  /** 打开编辑弹窗 */
  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({ name: user.name, role: user.role });
    setModalOpen(true);
  };

  /** 提交新建/编辑表单 */
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingUser) {
        await updateUser(editingUser.id, values as UserUpdate);
        messageApi.success('用户已更新');
      } else {
        await createUser(values as UserCreate);
        messageApi.success('用户已创建');
      }
      setModalOpen(false);
      load();
    } catch {
      /* 表单校验失败或请求失败 */
    }
  };

  /** 切换用户启用/禁用状态 */
  const handleToggleActive = async (user: User, checked: boolean) => {
    try {
      await updateUser(user.id, { is_active: checked });
      messageApi.success(checked ? '已启用' : '已禁用');
      load();
    } catch {
      messageApi.error('操作失败');
    }
  };

  /** 删除用户 */
  const handleDelete = async (id: number) => {
    try {
      await deleteUser(id);
      messageApi.success('用户已删除');
      load();
    } catch {
      messageApi.error('删除失败');
    }
  };

  /** 打开重置密码弹窗 */
  const handleResetPwd = (userId: number) => {
    setPwdUserId(userId);
    pwdForm.resetFields();
    setPwdModalOpen(true);
  };

  /** 提交重置密码 */
  const handlePwdSubmit = async () => {
    try {
      const { password } = await pwdForm.validateFields();
      if (pwdUserId !== null) {
        await resetPassword(pwdUserId, password);
        messageApi.success('密码已重置');
        setPwdModalOpen(false);
      }
    } catch {
      /* ignore */
    }
  };

  const columns = [
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '姓名', dataIndex: 'name', key: 'name' },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={roleColorMap[role] || 'default'}>{role}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean, record: User) => (
        <Switch checked={active} onChange={(v) => handleToggleActive(record, v)} />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: User) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" onClick={() => handleResetPwd(record.id)}>重置密码</Button>
          <Popconfirm title="确认删除该用户？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      {contextHolder}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Title level={4} style={{ margin: 0 }}>用户管理</Title></Col>
        <Col>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新建用户</Button>
        </Col>
      </Row>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 条`,
        }}
      />

      {/* 新建/编辑用户弹窗 */}
      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          {!editingUser && (
            <>
              <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
                <Input />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true, message: '请选择角色' }]}>
            <Select options={roleOptions} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码弹窗 */}
      <Modal
        title="重置密码"
        open={pwdModalOpen}
        onOk={handlePwdSubmit}
        onCancel={() => setPwdModalOpen(false)}
        destroyOnClose
      >
        <Form form={pwdForm} layout="vertical">
          <Form.Item name="password" label="新密码" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
