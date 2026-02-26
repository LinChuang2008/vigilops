/**
 * 资源对比图组件
 * 显示多服务器资源使用率和网络带宽对比
 */
import { Row, Col, Card, Typography } from 'antd';
import ReactECharts from '../ThemedECharts';

const { Text } = Typography;

interface HostItem {
  id: string;
  hostname: string;
  latest_metrics?: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent?: number;
    net_send_rate_kb?: number;
    net_recv_rate_kb?: number;
  };
}

interface ResourceChartsProps {
  hosts: HostItem[];
}

export default function ResourceCharts({ hosts }: ResourceChartsProps) {
  /**
   * 多服务器资源对比图配置
   * 横向对比所有在线服务器的 CPU、内存、磁盘使用率
   */
  const resourceCompareOption = () => {
    const validHosts = hosts.filter(h => h.latest_metrics);
    if (validHosts.length === 0) return null;
    
    const names = validHosts.map(h => h.hostname);
    return {
      tooltip: { trigger: 'axis' as const },
      legend: { bottom: 0, data: ['CPU', '内存', '磁盘'] },
      xAxis: { 
        type: 'category' as const, 
        data: names, 
        axisLabel: { rotate: names.length > 3 ? 30 : 0, fontSize: 11 } 
      },
      yAxis: { 
        type: 'value' as const, 
        max: 100, 
        axisLabel: { formatter: '{value}%' } 
      },
      series: [
        { 
          name: 'CPU', 
          type: 'bar' as const, 
          data: validHosts.map(h => h.latest_metrics!.cpu_percent ?? 0), 
          itemStyle: { color: '#1677ff' }, 
          barMaxWidth: 40 
        },
        { 
          name: '内存', 
          type: 'bar' as const, 
          data: validHosts.map(h => h.latest_metrics!.memory_percent ?? 0), 
          itemStyle: { color: '#52c41a' }, 
          barMaxWidth: 40 
        },
        { 
          name: '磁盘', 
          type: 'bar' as const, 
          data: validHosts.map(h => h.latest_metrics!.disk_percent ?? 0), 
          itemStyle: { color: '#faad14' }, 
          barMaxWidth: 40 
        },
      ],
      grid: { top: 20, bottom: 60, left: 50, right: 20 },
    };
  };

  /**
   * 网络带宽对比图配置
   * 对比各服务器的上传/下载带宽使用情况
   */
  const networkCompareOption = () => {
    const networkHosts = hosts.filter(h => h.latest_metrics?.net_send_rate_kb != null);
    if (networkHosts.length === 0) return null;
    
    return {
      tooltip: { trigger: 'axis' as const },
      legend: { bottom: 0 },
      xAxis: { 
        type: 'category' as const, 
        data: networkHosts.map(h => h.hostname), 
        axisLabel: { rotate: networkHosts.length > 3 ? 30 : 0 } 
      },
      yAxis: { 
        type: 'value' as const, 
        axisLabel: { formatter: '{value} KB/s' } 
      },
      series: [
        { 
          name: '上传', 
          type: 'bar' as const, 
          data: networkHosts.map(h => h.latest_metrics!.net_send_rate_kb ?? 0), 
          itemStyle: { color: '#1677ff' } 
        },
        { 
          name: '下载', 
          type: 'bar' as const, 
          data: networkHosts.map(h => h.latest_metrics!.net_recv_rate_kb ?? 0), 
          itemStyle: { color: '#52c41a' } 
        },
      ],
      grid: { top: 20, bottom: 60, left: 60, right: 20 },
    };
  };

  const resOption = resourceCompareOption();
  const netOption = networkCompareOption();

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} md={12}>
        <Card title="资源使用率对比">
          {resOption ? (
            <ReactECharts option={resOption} style={{ height: 260 }} />
          ) : <Text type="secondary">暂无数据</Text>}
        </Card>
      </Col>
      <Col xs={24} md={12}>
        <Card title="网络带宽 (KB/s)">
          {netOption ? (
            <ReactECharts option={netOption} style={{ height: 260 }} />
          ) : <Text type="secondary">暂无数据</Text>}
        </Card>
      </Col>
    </Row>
  );
}