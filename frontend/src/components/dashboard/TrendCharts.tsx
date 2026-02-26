/**
 * 24小时趋势图组件
 * 显示 CPU、内存、告警、错误日志的24小时趋势
 */
import { Row, Col, Card } from 'antd';
import ReactECharts from '../ThemedECharts';

interface TrendPoint {
  hour: string;
  avg_cpu: number | null;
  avg_mem: number | null;
  alert_count: number;
  error_log_count: number;
}

interface TrendChartsProps {
  trends: TrendPoint[];
}

export default function TrendCharts({ trends }: TrendChartsProps) {
  if (trends.length === 0) {
    return null;
  }

  /**
   * 迷你趋势图配置 (Sparkline chart option)
   * 生成小型面积图，用于展示 24 小时趋势数据
   */
  const sparklineOption = (values: (number | null)[], color: string, title: string) => ({
    title: { 
      text: title, 
      left: 'center', 
      top: 0, 
      textStyle: { fontSize: 12, color: '#666' } 
    },
    tooltip: { 
      trigger: 'axis' as const, 
      formatter: (params: any) => params[0]?.value != null ? `${params[0].value}` : '无数据' 
    },
    xAxis: { 
      type: 'category' as const, 
      show: false, 
      data: values.map((_, i) => i) 
    },
    yAxis: { 
      type: 'value' as const, 
      show: false 
    },
    series: [{
      type: 'line' as const,
      data: values,
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: { color: `${color}33` }
    }],
    grid: { top: 25, bottom: 5, left: 5, right: 5 },
  });

  const cpuTrend = trends.map(t => t.avg_cpu);
  const memTrend = trends.map(t => t.avg_mem);
  const alertTrend = trends.map(t => t.alert_count);
  const errorTrend = trends.map(t => t.error_log_count);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} md={6}>
        <Card styles={{ body: { padding: '12px' } }}>
          <ReactECharts 
            option={sparklineOption(cpuTrend, '#1677ff', 'CPU 趋势 (24h)')} 
            style={{ height: 80 }} 
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card styles={{ body: { padding: '12px' } }}>
          <ReactECharts 
            option={sparklineOption(memTrend, '#52c41a', '内存趋势 (24h)')} 
            style={{ height: 80 }} 
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card styles={{ body: { padding: '12px' } }}>
          <ReactECharts 
            option={sparklineOption(alertTrend, '#faad14', '告警趋势 (24h)')} 
            style={{ height: 80 }} 
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} md={6}>
        <Card styles={{ body: { padding: '12px' } }}>
          <ReactECharts 
            option={sparklineOption(errorTrend, '#ff4d4f', '错误日志 (24h)')} 
            style={{ height: 80 }} 
          />
        </Card>
      </Col>
    </Row>
  );
}