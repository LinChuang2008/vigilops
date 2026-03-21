/**
 * 通知日志页面 (Notification Logs Page)
 * 
 * 完整的通知日志管理界面，支持：
 * - 多维度过滤搜索 (时间范围、状态、渠道、告警ID)
 * - 分页和排序
 * - 统计信息展示 
 * - 失败通知重试
 * - 实时刷新
 * - 详情查看
 */
import { useEffect, useState } from 'react';
import {
  Table,
  Card,
  Tag,
  Space,
  Button,
  Select,
  DatePicker,
  Input,
  Row,
  Col,
  Statistic,
  message,
  Modal,
  Tooltip,
  Divider,
} from 'antd';
import {
  ReloadOutlined,
  RestOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { notificationService } from '../services/alerts';
import type { NotificationLog } from '../services/alerts';
import { EmptyState, ErrorState } from '../components/StateComponents';
import PageHeader from '../components/PageHeader';

const { RangePicker } = DatePicker;
const { Option } = Select;

// 通知状态映射（text 使用 i18n key）
const STATUS_CONFIG = {
  sent: { color: 'success', icon: <CheckCircleOutlined />, textKey: 'notifications.statusSent' },
  failed: { color: 'error', icon: <ExclamationCircleOutlined />, textKey: 'notifications.statusFailed' },
  pending: { color: 'processing', icon: <ClockCircleOutlined />, textKey: 'notifications.statusPending' },
};

// 统计信息接口
interface NotificationStats {
  period_days: number;
  total_notifications: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  channel_statistics: {
    channel_name: string;
    channel_type: string;
    total_count: number;
    success_count: number;
    success_rate: number;
  }[];
}

export default function NotificationLogs() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<NotificationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [stats, setStats] = useState<NotificationStats | null>(null);
  const [channels, setChannels] = useState<any[]>([]);
  
  // 查询参数
  const [filters, setFilters] = useState({
    alert_id: '',
    channel_id: '',
    status: '',
    start_time: '',
    end_time: '',
    page: 1,
    page_size: 20,
  });
  
  // 分页信息
  const [pagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  
  // 详情模态框
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<NotificationLog | null>(null);

  // 获取通知日志
  const fetchLogs = async (params = filters) => {
    setLoading(true);
    setLoadError(null);
    try {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) {
          queryParams.append(key, value.toString());
        }
      });
      
      const { data } = await notificationService.listLogs(Object.fromEntries(queryParams));
      setLogs(Array.isArray(data) ? data : []);
    } catch (error) {
      setLoadError(error);
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取统计信息
  const fetchStats = async () => {
    try {
      const { data } = await fetch('/api/v1/notification-channels/logs/stats').then(res => res.json());
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  // 获取通知渠道列表
  const fetchChannels = async () => {
    try {
      const { data } = await notificationService.listChannels();
      setChannels(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to fetch channels:', error);
    }
  };

  // 重试失败的通知
  const retryNotification = async (logId: number) => {
    try {
      const response = await fetch(`/api/v1/notification-channels/logs/${logId}/retry`, {
        method: 'POST',
      }).then(res => res.json());
      
      if (response.success) {
        message.success(t('notifications.retrySuccess'));
        fetchLogs();
      } else {
        message.error(t('notifications.retryFailed', { message: response.message }));
      }
    } catch (error) {
      message.error(t('notifications.retryRequestFailed'));
      console.error('Retry failed:', error);
    }
  };

  // 查看详情
  const showDetail = (record: NotificationLog) => {
    setSelectedLog(record);
    setDetailModalVisible(true);
  };

  // 刷新数据
  const refreshData = () => {
    fetchLogs();
    fetchStats();
  };

  // 重置筛选条件
  const resetFilters = () => {
    const defaultFilters = {
      alert_id: '',
      channel_id: '',
      status: '',
      start_time: '',
      end_time: '',
      page: 1,
      page_size: 20,
    };
    setFilters(defaultFilters);
    fetchLogs(defaultFilters);
  };

  // 处理筛选条件变化
  const handleFilterChange = (key: string, value: any) => {
    const newFilters = { ...filters, [key]: value, page: 1 };
    setFilters(newFilters);
    fetchLogs(newFilters);
  };

  // 处理时间范围变化
  const handleDateRangeChange = (dates: any) => {
    if (dates && dates.length === 2) {
      const newFilters = {
        ...filters,
        start_time: dates[0].toISOString(),
        end_time: dates[1].toISOString(),
        page: 1,
      };
      setFilters(newFilters);
      fetchLogs(newFilters);
    } else {
      const newFilters = { ...filters, start_time: '', end_time: '', page: 1 };
      setFilters(newFilters);
      fetchLogs(newFilters);
    }
  };

  useEffect(() => {
    fetchLogs();
    fetchStats();
    fetchChannels();
  }, []);

  // 表格列配置
  const columns = [
    {
      title: t('notifications.sentAt'),
      dataIndex: 'sent_at',
      key: 'sent_at',
      width: 180,
      render: (time: string) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: t('notifications.alertId'),
      dataIndex: 'alert_id',
      key: 'alert_id',
      width: 100,
    },
    {
      title: t('notifications.notificationChannel'),
      dataIndex: 'channel_id',
      key: 'channel_id',
      width: 120,
      render: (channelId: number) => {
        const channel = channels.find(c => c.id === channelId);
        return channel ? (
          <Tooltip title={`${t('common.type')}: ${channel.type}`}>
            <Tag color={channel.is_enabled ? 'green' : 'gray'}>
              {channel.name}
            </Tag>
          </Tooltip>
        ) : channelId;
      },
    },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: keyof typeof STATUS_CONFIG) => {
        const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
        return (
          <Tag color={config.color} icon={config.icon}>
            {t(config.textKey)}
          </Tag>
        );
      },
    },
    {
      title: t('notifications.responseCode'),
      dataIndex: 'response_code',
      key: 'response_code',
      width: 100,
      render: (code: number | null) => {
        if (code === null) return '-';
        const color = code >= 200 && code < 300 ? 'success' : 'error';
        return <Tag color={color}>{code}</Tag>;
      },
    },
    {
      title: t('notifications.retries'),
      dataIndex: 'retries',
      key: 'retries',
      width: 100,
      render: (retries: number) => (
        <Tag color={retries > 0 ? 'warning' : 'default'}>
          {retries}
        </Tag>
      ),
    },
    {
      title: t('notifications.errorInfo'),
      dataIndex: 'error',
      key: 'error',
      ellipsis: { showTitle: false },
      render: (error: string | null) => error ? (
        <Tooltip title={error}>
          <span style={{ color: '#ff4d4f' }}>{error.substring(0, 50)}...</span>
        </Tooltip>
      ) : '-',
    },
    {
      title: t('common.actions'),
      key: 'action',
      width: 150,
      render: (_: unknown, record: NotificationLog) => (
        <Space size="small">
          <Tooltip title={t('notifications.viewDetail')}>
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => showDetail(record)}
              size="small"
            />
          </Tooltip>
          {record.status === 'failed' && record.retries < 3 && (
            <Tooltip title={t('notifications.retrySend')}>
              <Button
                type="link"
                icon={<RestOutlined />}
                onClick={() => retryNotification(record.id)}
                size="small"
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '20px' }}>
      <PageHeader title={t('notifications.logManagement')} />

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 20 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('notifications.totalNotifications')}
                value={stats.total_notifications}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('notifications.successRate')}
                value={stats.success_rate}
                precision={1}
                suffix="%"
                valueStyle={{ color: stats.success_rate > 90 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('notifications.successCount')}
                value={stats.success_count}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('notifications.failedCount')}
                value={stats.failed_count}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 筛选条件 */}
      <Card style={{ marginBottom: 20 }}>
        <Row gutter={16} align="middle">
          <Col span={4}>
            <Input
              placeholder={t('notifications.alertId')}
              value={filters.alert_id}
              onChange={(e) => handleFilterChange('alert_id', e.target.value)}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder={t('notifications.notificationChannel')}
              value={filters.channel_id}
              onChange={(value) => handleFilterChange('channel_id', value)}
              allowClear
              style={{ width: '100%' }}
            >
              {channels.map(channel => (
                <Option key={channel.id} value={channel.id}>
                  {channel.name} ({channel.type})
                </Option>
              ))}
            </Select>
          </Col>
          <Col span={3}>
            <Select
              placeholder={t('notifications.statusFilter')}
              value={filters.status}
              onChange={(value) => handleFilterChange('status', value)}
              allowClear
              style={{ width: '100%' }}
            >
              <Option value="sent">{t('notifications.statusSent')}</Option>
              <Option value="failed">{t('notifications.statusFailed')}</Option>
              <Option value="pending">{t('notifications.statusPending')}</Option>
            </Select>
          </Col>
          <Col span={6}>
            <RangePicker
              style={{ width: '100%' }}
              showTime
              onChange={handleDateRangeChange}
              placeholder={[t('notifications.startTime'), t('notifications.endTime')]}
            />
          </Col>
          <Col span={7}>
            <Space>
              <Button type="primary" icon={<ReloadOutlined />} onClick={refreshData}>
                {t('common.refresh')}
              </Button>
              <Button onClick={resetFilters}>{t('common.reset')}</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card>
        {loadError ? (
          <ErrorState error={loadError} onRetry={refreshData} />
        ) : (
          <Table
            dataSource={logs}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => t('notifications.showRange', { start: range[0], end: range[1], total }),
            }}
            size="small"
            scroll={{ x: 1000 }}
            locale={{
              emptyText: <EmptyState scene="notifications" onAction={() => window.location.href = '/notification-channels'} />,
            }}
          />
        )}
      </Card>

      {/* 详情模态框 */}
      <Modal
        title={t('notifications.notificationDetail')}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedLog && (
          <div>
            <Row gutter={16}>
              <Col span={12}>
                <strong>{t('notifications.alertIdLabel')}</strong> {selectedLog.alert_id}
              </Col>
              <Col span={12}>
                <strong>{t('notifications.channelIdLabel')}</strong> {selectedLog.channel_id}
              </Col>
            </Row>
            <Divider />
            <Row gutter={16}>
              <Col span={12}>
                <strong>{t('notifications.sendStatus')}</strong>
                <Tag color={STATUS_CONFIG[selectedLog.status as keyof typeof STATUS_CONFIG]?.color}>
                  {t(STATUS_CONFIG[selectedLog.status as keyof typeof STATUS_CONFIG]?.textKey)}
                </Tag>
              </Col>
              <Col span={12}>
                <strong>{t('notifications.responseCodeLabel')}</strong> {selectedLog.response_code || '-'}
              </Col>
            </Row>
            <Divider />
            <Row gutter={16}>
              <Col span={12}>
                <strong>{t('notifications.retriesLabel')}</strong> {selectedLog.retries}
              </Col>
              <Col span={12}>
                <strong>{t('notifications.sentAtLabel')}</strong> {dayjs(selectedLog.sent_at).format('YYYY-MM-DD HH:mm:ss')}
              </Col>
            </Row>
            {selectedLog.error && (
              <>
                <Divider />
                <div>
                  <strong>{t('notifications.errorInfoLabel')}</strong>
                  <div style={{ marginTop: 8, padding: 8, backgroundColor: '#f5f5f5', borderRadius: 4 }}>
                    {selectedLog.error}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}