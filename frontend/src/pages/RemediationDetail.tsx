/**
 * 自动修复详情页 (Remediation Detail Page)
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageBreadcrumb from '../components/PageBreadcrumb';
import { Card, Typography, Descriptions, Button, Space, Spin, message, Modal, Timeline, Tag } from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  RobotOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { remediationService } from '../services/remediation';
import type { Remediation } from '../services/remediation';
import { RemediationStatusTag, RiskLevelTag } from '../components/RemediationBadge';

export default function RemediationDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Remediation | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const { data: res } = await remediationService.get(id);
      setData(res);
    } catch {
      messageApi.error(t('remediation.fetchFailed'));
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchDetail(); }, [id]);

  const handleAction = async (action: 'approve' | 'reject' | 'retry') => {
    if (!id) return;
    const confirmMap = {
      approve: t('remediation.confirmApprove'),
      reject: t('remediation.confirmReject'),
      retry: t('remediation.confirmRetry'),
    };
    const labelMap = {
      approve: t('remediation.approve'),
      reject: t('remediation.reject'),
      retry: t('remediation.retry'),
    };
    Modal.confirm({
      title: confirmMap[action],
      onOk: async () => {
        setActionLoading(true);
        try {
          await remediationService[action](id);
          messageApi.success(`${labelMap[action]} OK`);
          fetchDetail();
        } catch {
          messageApi.error(`${labelMap[action]} ${t('common.failed')}`);
        } finally { setActionLoading(false); }
      },
    });
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;
  if (!data) return <Typography.Text type="danger">{t('remediation.notFound')}</Typography.Text>;

  return (
    <div>
      {contextHolder}
      <PageBreadcrumb items={[{ label: t('remediation.title'), path: '/remediations' }, { label: t('remediation.detailTitle') }]} />
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/remediations')}>{t('common.backToList')}</Button>
      </Space>

      <Typography.Title level={4}>{t('remediation.detailTitle')}</Typography.Title>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label={t('remediation.alertNameLabel')}>{data.alert_name}</Descriptions.Item>
          <Descriptions.Item label={t('remediation.hostLabel')}>{data.host}</Descriptions.Item>
          <Descriptions.Item label={t('remediation.statusLabel')}><RemediationStatusTag status={data.status} /></Descriptions.Item>
          <Descriptions.Item label={t('remediation.riskLevelLabel')}><RiskLevelTag level={data.risk_level} /></Descriptions.Item>
          <Descriptions.Item label={t('remediation.runbookLabel')}>{data.runbook_name}</Descriptions.Item>
          <Descriptions.Item label={t('remediation.createdAtLabel')}>{new Date(data.created_at).toLocaleString()}</Descriptions.Item>
          {data.approved_by && (
            <Descriptions.Item label={t('remediation.approvedByLabel')}>{data.approved_by}</Descriptions.Item>
          )}
          {data.approved_at && (
            <Descriptions.Item label={t('remediation.approvedAtLabel')}>{new Date(data.approved_at).toLocaleString()}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card
        title={<><RobotOutlined style={{ marginRight: 8 }} />{t('remediation.aiDiagnosis')}</>}
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
          {data.diagnosis || t('remediation.noDiagnosis')}
        </div>
      </Card>

      <Card
        title={<><CodeOutlined style={{ marginRight: 8 }} />{t('remediation.commandLogs')}</>}
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
          <Typography.Text type="secondary">{t('remediation.noCommands')}</Typography.Text>
        )}
      </Card>

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
                {t('remediation.approve')}
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                loading={actionLoading}
                onClick={() => handleAction('reject')}
              >
                {t('remediation.reject')}
              </Button>
            </>
          )}
          {data.status === 'failed' && (
            <Button
              icon={<ReloadOutlined />}
              loading={actionLoading}
              onClick={() => handleAction('retry')}
            >
              {t('remediation.retry')}
            </Button>
          )}
        </Space>
      </Card>
    </div>
  );
}
