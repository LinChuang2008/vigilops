/**
 * 日志统计组件
 * 显示最近1小时的日志统计数据和分布图
 */
import { Card, Row, Col, Statistic, Tag, Typography } from 'antd';
import ReactECharts from '../ThemedECharts';
import type { LogStats as LogStatsType } from '../../services/logs';

const { Text } = Typography;

interface LogStatsProps {
  logStats: LogStatsType | null;
}

export default function LogStats({ logStats }: LogStatsProps) {
  if (!logStats || logStats.by_level.length === 0) {
    return (
      <Card title="最近 1 小时日志统计">
        <Text type="secondary">暂无数据</Text>
      </Card>
    );
  }

  const totalLogs = logStats.by_level.reduce((sum, level) => sum + level.count, 0);
  
  const levelColors: Record<string, string> = {
    DEBUG: '#bfbfbf',
    INFO: '#1677ff', 
    WARN: '#faad14',
    ERROR: '#ff4d4f',
    FATAL: '#722ed1'
  };

  const levelTagColors: Record<string, string> = {
    DEBUG: 'default',
    INFO: 'blue',
    WARN: 'orange', 
    ERROR: 'red',
    FATAL: 'purple'
  };

  const pieOption = {
    tooltip: { trigger: 'item' as const },
    series: [{
      type: 'pie' as const,
      radius: ['40%', '70%'],
      data: logStats.by_level
        .filter(l => l.count > 0)
        .map(({ level, count }) => ({
          name: level,
          value: count,
          itemStyle: { color: levelColors[level] || '#999' },
        })),
      label: { formatter: '{b}: {c}' },
    }],
  };

  return (
    <Card title="最近 1 小时日志统计">
      <Row gutter={16} align="middle">
        <Col xs={24} md={8}>
          <Statistic title="日志总量" value={totalLogs} />
          <div style={{ marginTop: 8 }}>
            {logStats.by_level.map(({ level, count }) => (
              <Tag 
                key={level} 
                color={levelTagColors[level] || 'default'}
                style={{ marginBottom: 4 }}
              >
                {level}: {count}
              </Tag>
            ))}
          </div>
        </Col>
        <Col xs={24} md={16}>
          <ReactECharts 
            option={pieOption}
            style={{ height: 200 }} 
          />
        </Col>
      </Row>
    </Card>
  );
}