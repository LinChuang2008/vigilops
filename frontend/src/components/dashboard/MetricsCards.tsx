/**
 * 核心指标卡片组件
 * 显示服务器、服务、数据库统计和健康评分
 */
import { Row, Col, Card, Statistic, Tag, Progress } from 'antd';
import {
  CloudServerOutlined, ApiOutlined, AlertOutlined,
  CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import { Typography } from 'antd';
import type { DatabaseItem } from '../../services/databases';

const { Text } = Typography;

interface MetricsCardsProps {
  hostTotal: number;
  hostOnline: number;
  hostOffline: number;
  svcTotal: number;
  svcHealthy: number;
  svcUnhealthy: number;
  alertFiring: number;
  healthScore: number;
  dbItems: DatabaseItem[];
}

export default function MetricsCards({
  hostTotal, hostOnline, hostOffline,
  svcTotal, svcHealthy, svcUnhealthy,
  alertFiring, healthScore, dbItems,
}: MetricsCardsProps) {
  const scoreColor = healthScore > 80 ? '#52c41a' : healthScore >= 60 ? '#faad14' : '#ff4d4f';

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} md={5}>
        <Card>
          <Statistic title="服务器" value={hostTotal} prefix={<CloudServerOutlined />} />
          <div style={{ marginTop: 8 }}>
            <Tag icon={<CheckCircleOutlined />} color="success">在线 {hostOnline}</Tag>
            <Tag icon={<CloseCircleOutlined />} color="error">离线 {hostOffline}</Tag>
          </div>
        </Card>
      </Col>
      <Col xs={24} sm={12} md={5}>
        <Card>
          <Statistic title="服务" value={svcTotal} prefix={<ApiOutlined />} />
          <div style={{ marginTop: 8 }}>
            <Tag color="success">健康 {svcHealthy}</Tag>
            <Tag color="error">异常 {svcUnhealthy}</Tag>
          </div>
        </Card>
      </Col>
      <Col xs={24} sm={12} md={5}>
        <Card>
          <Statistic title="数据库" value={dbItems.length} prefix={<DatabaseOutlined />} />
          <div style={{ marginTop: 8 }}>
            <Tag color="success">健康 {dbItems.filter(x => x.status === 'healthy').length}</Tag>
            <Tag color="error">异常 {dbItems.filter(x => x.status !== 'healthy' && x.status !== 'unknown').length}</Tag>
          </div>
        </Card>
      </Col>
      <Col xs={24} sm={12} md={5}>
        <Card>
          <Statistic 
            title="活跃告警" 
            value={alertFiring} 
            prefix={<AlertOutlined />}
            valueStyle={{ color: alertFiring > 0 ? '#cf1322' : '#3f8600' }} 
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={4}>
        <Card style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 14 }}>健康评分</Text>
          <div style={{ marginTop: 8 }}>
            <Progress 
              type="circle" 
              percent={healthScore} 
              size={80} 
              strokeColor={scoreColor}
              format={(p) => <span style={{ color: scoreColor, fontWeight: 'bold' }}>{p}</span>} 
            />
          </div>
        </Card>
      </Col>
    </Row>
  );
}