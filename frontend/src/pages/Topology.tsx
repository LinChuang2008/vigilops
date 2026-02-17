/**
 * 服务拓扑图页面
 *
 * 支持两种布局模式：
 * 1. 分层架构布局（默认）—— 按服务类型分为前端层、应用层、中间件层、数据层，从左到右排列
 * 2. 力导向布局 —— ECharts 原生力导向图
 *
 * 节点形状和颜色区分服务类型，连线样式区分依赖类型。
 */
import { useEffect, useRef, useState } from 'react';
import { Typography, Button, Spin, message, Radio } from 'antd';
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
  port?: number | string;
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

/** 布局模式 */
type LayoutMode = 'layered' | 'force';

/* ==================== 分层分类逻辑 ==================== */

/** 层级定义：从左到右 4 列 */
const LAYERS = [
  { key: 'frontend', x: 150, label: '前端层', patterns: [/frontend/i, /web/i, /nginx/i, /前端/] },
  { key: 'app', x: 400, label: '应用层', patterns: [/backend/i, /api/i, /app/i, /service/i, /admin/i, /job/i] },
  { key: 'middleware', x: 650, label: '中间件层', patterns: [/rabbitmq/i, /\bmq\b/i, /nacos/i, /注册中心/, /clickhouse/i] },
  { key: 'data', x: 900, label: '数据层', patterns: [/postgres/i, /mysql/i, /redis/i, /oracle/i, /\bdb\b/i, /cache/i] },
];

/** 根据服务名判断所属层级，无法分类的归入应用层 */
const getLayer = (name: string): (typeof LAYERS)[number] => {
  for (const layer of LAYERS) {
    if (layer.patterns.some((p) => p.test(name))) return layer;
  }
  return LAYERS[1]; // 默认：应用层
};

/* ==================== 节点样式逻辑 ==================== */

/** 服务类型样式配置 */
interface NodeStyle {
  symbol: string;
  color: string;
  label: string;
}

/** 根据服务名推断节点样式 */
const getNodeStyle = (name: string): NodeStyle => {
  const lower = name.toLowerCase();
  // 数据库类
  if (/postgres|mysql|oracle|\bdb\b/i.test(lower)) {
    return { symbol: 'roundRect', color: '#7B68EE', label: '数据库' };
  }
  // 缓存类
  if (/redis|cache/i.test(lower)) {
    return { symbol: 'diamond', color: '#9ACD32', label: '缓存' };
  }
  // 消息队列
  if (/rabbitmq|\bmq\b/i.test(lower)) {
    return { symbol: 'triangle', color: '#00CED1', label: '消息队列' };
  }
  // 前端/Web
  if (/frontend|web|nginx|前端/i.test(lower)) {
    return { symbol: 'circle', color: '#FFB800', label: '前端/Web' };
  }
  // 后端/API
  if (/backend|api|app|service|admin|job/i.test(lower)) {
    return { symbol: 'rect', color: '#FF7F50', label: '后端/API' };
  }
  // 其他
  return { symbol: 'circle', color: '#708090', label: '其他' };
};

/** 根据依赖类型返回连线样式 */
const getEdgeStyle = (type: string) => {
  if (type === 'calls') {
    return { type: 'solid' as const, showArrow: true };
  }
  if (type === 'depends_on') {
    return { type: 'dashed' as const, showArrow: true };
  }
  // co-located 同主机
  return { type: 'solid' as const, showArrow: false };
};

/* ==================== 分层布局坐标计算 ==================== */

/** 计算分层布局中每个节点的 x, y 坐标 */
const computeLayeredPositions = (nodes: TopoNode[]): Map<number, { x: number; y: number }> => {
  // 将节点按层分组
  const layerBuckets = new Map<string, TopoNode[]>();
  for (const layer of LAYERS) {
    layerBuckets.set(layer.key, []);
  }
  for (const node of nodes) {
    const layer = getLayer(node.name);
    layerBuckets.get(layer.key)!.push(node);
  }

  const positions = new Map<number, { x: number; y: number }>();
  const startY = 60;
  const minSpacing = 80; // 最小纵向间距

  for (const layer of LAYERS) {
    const bucket = layerBuckets.get(layer.key)!;
    if (bucket.length === 0) continue;

    // 动态计算间距，保证不重叠
    const totalHeight = Math.max(600, bucket.length * minSpacing);
    const spacing = totalHeight / (bucket.length + 1);

    bucket.forEach((node, index) => {
      positions.set(node.id, {
        x: layer.x,
        y: startY + (index + 1) * spacing,
      });
    });
  }

  return positions;
};

/* ==================== 组件 ==================== */

export default function Topology() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [loading, setLoading] = useState(false);
  const [layout, setLayout] = useState<LayoutMode>('layered');
  const topoData = useRef<TopologyData | null>(null);

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
      topoData.current = data;
      renderChart(data, layout);
    } catch {
      message.error('加载拓扑数据失败');
    } finally {
      setLoading(false);
    }
  };

  /** 渲染图表（根据布局模式） */
  const renderChart = (data: TopologyData, mode: LayoutMode) => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const chart = chartInstance.current;

    // 构建节点 ID → 名称映射
    const idMap = new Map<number, string>();
    data.nodes.forEach((n) => idMap.set(n.id, n.name));

    // 分层布局坐标
    const positions = mode === 'layered' ? computeLayeredPositions(data.nodes) : null;

    // 构建图例数据（按节点样式类型去重）
    const legendSet = new Map<string, string>();
    data.nodes.forEach((n) => {
      const style = getNodeStyle(n.name);
      legendSet.set(style.label, style.color);
    });

    const nodes = data.nodes.map((n) => {
      const style = getNodeStyle(n.name);
      const pos = positions?.get(n.id);
      return {
        id: String(n.id),
        name: n.name,
        symbol: style.symbol,
        symbolSize: 45,
        // 分层布局使用固定坐标
        ...(pos ? { x: pos.x, y: pos.y, fixed: true } : {}),
        itemStyle: {
          color: style.color,
          borderColor: '#fff',
          borderWidth: 2,
          shadowColor: 'rgba(0,0,0,0.15)',
          shadowBlur: 6,
        },
        label: {
          show: true,
          position: 'bottom' as const,
          fontSize: 12,
          color: '#333',
          formatter: '{b}',
        },
        tooltip: {
          formatter: `<b>${n.name}</b><br/>` +
            `类型: ${n.type}<br/>` +
            `状态: ${n.status}<br/>` +
            `主机: ${n.host || '—'}<br/>` +
            `端口: ${(n as any).port || '—'}`,
        },
        category: style.label,
      };
    });

    // 图例分类
    const categories = Array.from(legendSet.entries()).map(([name, color]) => ({
      name,
      itemStyle: { color },
    }));

    const edges = data.edges.map((e) => {
      const style = getEdgeStyle(e.type);
      return {
        source: String(e.source),
        target: String(e.target),
        lineStyle: {
          type: style.type,
          color: '#999',
          width: e.type === 'co-located' ? 1 : 1.5,
        },
        // 箭头
        ...(style.showArrow
          ? { edgeSymbol: ['none', 'arrow'], edgeSymbolSize: [0, 8] }
          : { edgeSymbol: ['none', 'none'] }),
        tooltip: {
          formatter: `${idMap.get(e.source) ?? e.source} → ${idMap.get(e.target) ?? e.target}<br/>类型: ${e.type}<br/>${e.description}`,
        },
      };
    });

    // 层级标签（仅分层模式显示）
    const graphicElements = mode === 'layered'
      ? LAYERS.map((layer) => ({
          type: 'text' as const,
          left: layer.x - 30,
          top: 15,
          style: {
            text: layer.label,
            fontSize: 14,
            fontWeight: 'bold' as const,
            fill: '#666',
          },
        }))
      : [];

    const option: echarts.EChartsOption = {
      tooltip: { trigger: 'item' },
      legend: {
        data: categories.map((c) => c.name),
        orient: 'vertical',
        right: 20,
        top: 60,
        textStyle: { fontSize: 12 },
        itemWidth: 16,
        itemHeight: 12,
      },
      graphic: graphicElements,
      animationDuration: 600,
      series: [
        {
          type: 'graph',
          layout: mode === 'layered' ? 'none' : 'force',
          roam: true,
          draggable: true,
          categories,
          data: nodes,
          links: edges,
          // 力导向参数（仅力导向模式生效）
          ...(mode === 'force'
            ? {
                force: {
                  repulsion: 300,
                  edgeLength: [120, 250],
                  gravity: 0.1,
                },
              }
            : {}),
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 3 },
          },
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: [0, 8],
          lineStyle: {
            color: '#999',
            width: 1.5,
          },
        },
      ],
    };

    chart.setOption(option, true);
    chart.resize();
  };

  /** 切换布局模式 */
  const handleLayoutChange = (mode: LayoutMode) => {
    setLayout(mode);
    if (topoData.current) {
      renderChart(topoData.current, mode);
    }
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
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Radio.Group
            value={layout}
            onChange={(e) => handleLayoutChange(e.target.value)}
            optionType="button"
            buttonStyle="solid"
            size="small"
          >
            <Radio.Button value="layered">分层布局</Radio.Button>
            <Radio.Button value="force">力导向布局</Radio.Button>
          </Radio.Group>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        </div>
      </div>
      <Spin spinning={loading}>
        <div ref={chartRef} style={{ width: '100%', height: 'calc(100vh - 220px)', minHeight: 700 }} />
      </Spin>
    </div>
  );
}
