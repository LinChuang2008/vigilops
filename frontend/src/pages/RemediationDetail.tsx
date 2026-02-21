/**
 * 自动修复详情页 (Remediation Detail Page)
 *
 * 功能：展示单个修复任务的完整信息，包括 AI 诊断结果、命令执行日志、审批操作
 * 数据源：GET /api/v1/remediations/:id
 * 路由参数：id - 修复任务ID
 *
 * 页面结构：
 *   1. 基本信息卡片 - 告警名称、主机、状态、风险级别、Runbook、审批人等
 *   2. AI 诊断结果 - 展示 AI 引擎对告警的分析和修复建议（monospace 格式）
 *   3. 命令执行日志 - Timeline 形式展示每条命令的执行状态、输出（终端风格渲染）
 *   4. 操作按钮 - pending 状态显示审批/拒绝，failed 状态显示重试
 *
 * 交互操作：
 *   - approve: 审批通过 → 触发自动执行修复命令
 *   - reject: 拒绝修复
 *   - retry: 失败后重新执行
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Descriptions, Button, Space, Spin, message, Modal, Timeline, Tag } from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  RobotOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { remediationService } from '../services/remediation';
import type { Remediation } from '../services/remediation';
import { RemediationStatusTag, RiskLevelTag } from '../components/RemediationBadge';

export default function RemediationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Remediation | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const fetch = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const { data: res } = await remediationService.get(id);
      setData(res);
    } catch {
      messageApi.error('获取详情失败');
    } finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, [id]);

  const handleAction = async (action: 'approve' | 'reject' | 'retry') => {
    if (!id) return;
    const labels = { approve: '审批通过', reject: '拒绝', retry: '重新执行' };
    Modal.confirm({
      title: `确认${labels[action]}？`,
      onOk: async () => {
        setActionLoading(true);
        try {
          await remediationService[action](id);
          messageApi.success(`${labels[action]}成功`);
          fetch();
        } catch {
          messageApi.error(`${labels[action]}失败`);
        } finally { setActionLoading(false); }
      },
    });
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  if (!data) return <Typography.Text type="danger">未找到修复记录</Typography.Text>;

  return (
    <div>
      {contextHolder}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/remediations')}>返回列表</Button>
      </Space>

      <Typography.Title level={4}>修复详情</Typography.Title>

      {/* 基本信息 */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="告警名称">{data.alert_name}</Descriptions.Item>
          <Descriptions.Item label="主机">{data.host}</Descriptions.Item>
          <Descriptions.Item label="状态"><RemediationStatusTag status={data.status} /></Descriptions.Item>
          <Descriptions.Item label="风险级别"><RiskLevelTag level={data.risk_level} /></Descriptions.Item>
          <Descriptions.Item label="Runbook">{data.runbook}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{new Date(data.created_at).toLocaleString()}</Descriptions.Item>
          {data.approved_by && (
            <Descriptions.Item label="审批人">{data.approved_by}</Descriptions.Item>
          )}
          {data.approved_at && (
            <Descriptions.Item label="审批时间">{new Date(data.approved_at).toLocaleString()}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* AI 诊断结果 */}
      <Card
        title={<><RobotOutlined style={{ marginRight: 8 }} />AI 诊断结果</>}
        style={{ marginBottom: 16 }}
      >
        <div style={{
          background: '#f6f8fa',
          padding: 16,
          borderRadius: 6,
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
          fontSize: 13,
          lineHeight: 1.6,
        }}>
          {data.diagnosis || '暂无诊断信息'}
        </div>
      </Card>

      {/* 命令执行日志 */}
      <Card
        title={<><CodeOutlined style={{ marginRight: 8 }} />命令执行日志</>}
        style={{ marginBottom: 16 }}
      >
        {data.commands && data.commands.length > 0 ? (
          <Timeline
            items={data.commands.map((cmd, i) => ({
              color: cmd.exit_code === 0 ? 'green' : 'red',
              children: (
                <div key={i}>
                  <div style={{ marginBottom: 4 }}>
                    <Tag color={cmd.exit_code === 0 ? 'success' : 'error'}>
                      exit: {cmd.exit_code}
                    </Tag>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {cmd.executed_at ? new Date(cmd.executed_at).toLocaleString() : ''}
                    </Typography.Text>
                  </div>
                  <div style={{
                    background: '#1e1e1e',
                    color: '#d4d4d4',
                    padding: '8px 12px',
                    borderRadius: 4,
                    fontFamily: 'monospace',
                    fontSize: 13,
                    marginBottom: 4,
                  }}>
                    $ {cmd.command}
                  </div>
                  {cmd.output && (
                    <div style={{
                      background: '#f6f8fa',
                      padding: '8px 12px',
                      borderRadius: 4,
                      fontFamily: 'monospace',
                      fontSize: 12,
                      whiteSpace: 'pre-wrap',
                      maxHeight: 200,
                      overflow: 'auto',
                    }}>
                      {cmd.output}
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        ) : (
          <Typography.Text type="secondary">暂无执行记录</Typography.Text>
        )}
      </Card>

      {/* 操作按钮 */}
      <Card>
        <Space>
          {data.status === 'pending' && (
            <>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                loading={actionLoading}
                onClick={() => handleAction('approve')}
              >
                审批通过
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                loading={actionLoading}
                onClick={() => handleAction('reject')}
              >
                拒绝
              </Button>
            </>
          )}
          {data.status === 'failed' && (
            <Button
              icon={<ReloadOutlined />}
              loading={actionLoading}
              onClick={() => handleAction('retry')}
            >
              重新执行
            </Button>
          )}
        </Space>
      </Card>
    </div>
  );
}
