/**
 * 登录/注册页面
 *
 * 提供邮箱密码登录和注册功能，通过 Tabs 切换两种模式。
 * 登录或注册成功后将 token 和用户信息存入 localStorage，并跳转到首页。
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, message, Tabs, Row, Col, Space } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, RocketOutlined, RobotOutlined, ThunderboltOutlined, DashboardOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { authService } from '../services/auth';

const { Title } = Typography;

/**
 * 登录注册页面组件
 *
 * 包含登录和注册两个 Tab，共用加载状态。登录/注册成功后自动获取用户信息并跳转。
 */
export default function Login() {
  /** 按钮加载状态（登录/注册共用） */
  const [loading, setLoading] = useState(false);
  /** 当前激活的 Tab（login | register） */
  const [activeTab, setActiveTab] = useState('login');
  const navigate = useNavigate();
  const [loginForm] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  /** 处理登录：调用登录接口，存储 token，获取用户信息后跳转首页 */
  const handleLogin = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const { data } = await authService.login(values);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      // 获取用户信息并存储用户名
      const { data: user } = await authService.me();
      localStorage.setItem('user_name', user.name);
      localStorage.setItem('user_role', user.role);
      messageApi.success('登录成功');
      navigate('/');
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      messageApi.error(err.response?.data?.detail || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  /** 处理注册：调用注册接口，流程与登录类似 */
  const handleRegister = async (values: { email: string; name: string; password: string }) => {
    setLoading(true);
    try {
      const { data } = await authService.register(values);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      const { data: user } = await authService.me();
      localStorage.setItem('user_name', user.name);
      localStorage.setItem('user_role', user.role);
      messageApi.success('注册成功');
      navigate('/');
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      messageApi.error(err.response?.data?.detail || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      {contextHolder}
      <Card style={{ width: 860, maxWidth: '95vw', boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
        <Row gutter={32}>
          {/* 左侧产品特性 */}
          <Col xs={0} md={12} style={{ borderRight: '1px solid #f0f0f0', display: 'flex', alignItems: 'center' }}>
            <div style={{ padding: '24px 16px' }}>
              <Title level={2} style={{ marginBottom: 8 }}>VigilOps</Title>
              <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 32, fontSize: 15 }}>
                AI 智能运维监控平台
              </Typography.Text>
              <Space direction="vertical" size={24} style={{ width: '100%' }}>
                {[
                  { icon: <RobotOutlined style={{ fontSize: 28, color: '#667eea' }} />, title: 'AI 智能分析', desc: '基于 AI 的根因分析与运维洞察' },
                  { icon: <ThunderboltOutlined style={{ fontSize: 28, color: '#faad14' }} />, title: '自动修复', desc: '内置 Runbook，告警触发自动修复' },
                  { icon: <DashboardOutlined style={{ fontSize: 28, color: '#52c41a' }} />, title: '实时监控', desc: 'WebSocket 实时推送，秒级感知' },
                  { icon: <SafetyCertificateOutlined style={{ fontSize: 28, color: '#1677ff' }} />, title: 'SLA 管理', desc: '可用性追踪与错误预算管理' },
                ].map((item, i) => (
                  <Space key={i} align="start" size={12}>
                    <div style={{ width: 48, height: 48, borderRadius: 12, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {item.icon}
                    </div>
                    <div>
                      <Typography.Text strong>{item.title}</Typography.Text>
                      <br />
                      <Typography.Text type="secondary" style={{ fontSize: 13 }}>{item.desc}</Typography.Text>
                    </div>
                  </Space>
                ))}
              </Space>
            </div>
          </Col>
          {/* 右侧登录表单 */}
          <Col xs={24} md={12}>
            <div style={{ padding: '24px 8px' }}>
              <Title level={3} style={{ textAlign: 'center', marginBottom: 8, display: 'none' }}>VigilOps</Title>
              {/* Mobile-only title */}
              <div className="login-mobile-title" style={{ textAlign: 'center', marginBottom: 16 }}>
                <Title level={3} style={{ margin: 0 }}>VigilOps</Title>
                <Typography.Text type="secondary">AI 智能运维监控平台</Typography.Text>
              </div>
        <Tabs activeKey={activeTab} onChange={setActiveTab} centered items={[
          {
            key: 'login',
            label: '登录',
            children: (
              <Form form={loginForm} onFinish={handleLogin} size="large">
                <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
                  <Input prefix={<MailOutlined />} placeholder="邮箱" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
                </Form.Item>
                <div style={{ textAlign: 'center' }}>
                  <Button
                    type="link"
                    icon={<RocketOutlined />}
                    onClick={() => {
                      loginForm.setFieldsValue({ email: 'demo@vigilops.io', password: 'demo123' });
                      loginForm.submit();
                    }}
                  >
                    🚀 Demo 体验（只读账号，无需注册）
                  </Button>
                </div>
              </Form>
            ),
          },
          {
            key: 'register',
            label: '注册',
            children: (
              <Form onFinish={handleRegister} size="large">
                <Form.Item name="email" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
                  <Input prefix={<MailOutlined />} placeholder="邮箱" />
                </Form.Item>
                <Form.Item name="name" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input prefix={<UserOutlined />} placeholder="用户名" />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                  <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>注册</Button>
                </Form.Item>
              </Form>
            ),
          },
        ]} />
            </div>
          </Col>
        </Row>
      </Card>
      <div style={{ marginTop: 24, textAlign: 'center', color: 'rgba(255,255,255,0.6)', fontSize: 12, lineHeight: 1.8 }}>
        <div>琳创科技（LinChuang Technology）</div>
        <div>contact@lchuangnet.com · <a href="https://lchuangnet.com" style={{ color: 'rgba(255,255,255,0.6)' }}>lchuangnet.com</a></div>
      </div>
    </div>
  );
}
