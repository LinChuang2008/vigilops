/**
 * 服务拓扑图页面
 *
 * 使用 ECharts 力导向图展示服务间的依赖关系和健康状态。
 * 节点颜色反映服务状态（绿=up / 红=down / 灰=unknown），
 * 边的线型区分依赖类型（实线=calls / 虚线=depends_on / 点线=co-located）。
 */
import { useEffect, useRef, useState } from 'react';
import { Typography, Button, Spin, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import * as echarts from 'echarts';

const { Title } = Typography;

/** 节点数据接口 */
interface TopoNode {
  id: number;
  name: string;
  type: string;
  status: string;
  host: string;
  group: string;
}

/** 边数据接口 */
interface TopoEdge {
  source: number;
  target: number;
  type: string;
  description: string;
}

/** API 返回的拓扑数据 */
interface TopologyData {
  nodes: TopoNode[];
  edges: TopoEdge[];
}

/** 根据服务状态返回颜色 */
const statusColor = (status: string) => {
  if (status === 'up') return '#52c41a';
  if (status === 'down') return '#ff4d4f';
  return '#bfbfbf';
};

/** 根据服务分组返回图标符号 */
const groupSymbol = (group: string): string => {
  switch (group) {
    case 'database': return 'roundRect';
    case 'cache': return 'diamond';
    case 'mq': return 'triangle';
    case 'web': return 'rect';
    case 'api': return 'circle';
    default: return 'circle';
  }
};

/** 根据依赖类型返回线型 */
const edgeLineType = (type: string): string => {
  if (type === 'depends_on') return 'dashed';
  if (type === 'co-located') return 'dotted';
  return 'solid';
};

export default function Topology() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [loading, setLoading] = useState(false);

  /** 从后端加载拓扑数据 */
  const fetchData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/topology', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('请求失败');
      const data: TopologyData = await res.json();
      renderChart(data);
    } catch {
      message.error('加载拓扑数据失败');
    } finally {
      setLoading(false);
    }
  };

  /** 渲染 ECharts 力导向图 */
  const renderChart = (data: TopologyData) => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const chart = chartInstance.current;

    // 构建节点 ID → 名称映射
    const idMap = new Map<number, string>();
    data.nodes.forEach((n) => idMap.set(n.id, n.name));

    const nodes = data.nodes.map((n) => ({
      id: String(n.id),
      name: n.name,
      symbol: groupSymbol(n.group),
      symbolSize: n.group === 'web' ? 50 : 40,
      itemStyle: { color: statusColor(n.status), borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 11, color: '#333' },
      tooltip: {
        formatter: `<b>${n.name}</b><br/>类型: ${n.type}<br/>状态: ${n.status}<br/>主机: ${n.host || '无'}<br/>分组: ${n.group}`,
      },
      // 用于力导向分组
      category: n.group,
    }));

    const categories = [...new Set(data.nodes.map((n) => n.group))].map((g) => ({ name: g }));

    const edges = data.edges.map((e) => ({
      source: String(e.source),
      target: String(e.target),
      lineStyle: {
        type: edgeLineType(e.type) as 'solid' | 'dashed' | 'dotted',
        color: '#aaa',
        width: 1.5,
        curveness: 0.2,
      },
      tooltip: { formatter: `${idMap.get(e.source) ?? e.source} → ${idMap.get(e.target) ?? e.target}<br/>类型: ${e.type}<br/>${e.description}` },
    }));

    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: {
        data: categories.map((c) => c.name),
        orient: 'vertical',
        right: 10,
        top: 20,
        textStyle: { fontSize: 12 },
      },
      animationDuration: 800,
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          categories,
          data: nodes,
          links: edges,
          force: {
            repulsion: 300,
            edgeLength: [120, 250],
            gravity: 0.1,
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 3 },
          },
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: [0, 8],
        },
      ],
    }, true);

    chart.resize();
  };

  useEffect(() => {
    fetchData();

    // 监听窗口大小变化
    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>服务拓扑</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
          刷新
        </Button>
      </div>
      <Spin spinning={loading}>
        <div ref={chartRef} style={{ width: '100%', height: 'calc(100vh - 220px)', minHeight: 500 }} />
      </Spin>
    </div>
  );
}
