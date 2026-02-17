/**
 * 服务拓扑图页面
 *
 * 使用 ECharts Graph 实现分类分组布局：
 * - 节点按服务类型分为 6 组，每组有独立区域
 * - 连线只显示真正的依赖关系（calls / depends_on），无 co-located 全连接
 * - 支持悬停高亮关联节点、节点状态色圈
 * - 支持分组布局和力导向布局切换
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { Typography, Button, Spin, message, Radio, Space, Tag } from 'antd';
import { ReloadOutlined, ApartmentOutlined, NodeIndexOutlined } from '@ant-design/icons';
import * as echarts from 'echarts';

const { Title } = Typography;

/** 节点数据接口 */
interface TopoNode {
  id: number;
  name: string;
  type: string;
  status: string;
  host: string;
  host_id?: number;
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
  hosts?: { id: number; name: string }[];
}

/** 布局模式 */
type LayoutMode = 'grouped' | 'force';

/* ==================== 分组配置 ==================== */

/** 服务分组定义 */
const GROUP_CONFIG: Record<string, {
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  order: number;
}> = {
  web:      { label: '🌐 前端服务',   icon: '🌐', color: '#FFB800', bgColor: 'rgba(255,184,0,0.08)',   order: 0 },
  api:      { label: '⚙️ 后端服务',   icon: '⚙️', color: '#FF7F50', bgColor: 'rgba(255,127,80,0.08)',  order: 1 },
  app:      { label: '📦 业务应用',   icon: '📦', color: '#4FC3F7', bgColor: 'rgba(79,195,247,0.08)',  order: 2 },
  registry: { label: '🔍 注册中心',   icon: '🔍', color: '#AB47BC', bgColor: 'rgba(171,71,188,0.08)',  order: 3 },
  mq:       { label: '📨 消息队列',   icon: '📨', color: '#00CED1', bgColor: 'rgba(0,206,209,0.08)',   order: 4 },
  olap:     { label: '📊 分析引擎',   icon: '📊', color: '#FF8A65', bgColor: 'rgba(255,138,101,0.08)', order: 5 },
  database: { label: '🗄️ 数据库',    icon: '🗄️', color: '#7B68EE', bgColor: 'rgba(123,104,238,0.08)', order: 6 },
  cache:    { label: '⚡ 缓存',      icon: '⚡', color: '#9ACD32', bgColor: 'rgba(154,205,50,0.08)',   order: 7 },
};

/** 状态颜色 */
const STATUS_COLORS: Record<string, string> = {
  up: '#52c41a',
  running: '#52c41a',
  healthy: '#52c41a',
  down: '#ff4d4f',
  stopped: '#ff4d4f',
  warning: '#faad14',
  unknown: '#d9d9d9',
};

/** 获取状态颜色 */
const getStatusColor = (status: string): string => {
  return STATUS_COLORS[status?.toLowerCase()] || STATUS_COLORS.unknown;
};

/** 清理服务名显示（缩短过长名称） */
const shortName = (name: string): string => {
  // 去掉端口后缀和容器编号
  let s = name.replace(/\s*\(:\d+\)/, '').replace(/-1$/, '');
  // 如果还是太长，截断
  if (s.length > 20) s = s.substring(0, 18) + '…';
  return s;
};

/* ==================== 分组布局坐标计算 ==================== */

/**
 * 将节点按 group 分组，每组在画布上分配独立矩形区域。
 * 使用 3 列 N 行网格布局。
 */
const computeGroupedPositions = (
  nodes: TopoNode[],
  width: number,
  height: number,
): { positions: Map<number, { x: number; y: number }>; groupBoxes: GroupBox[] } => {
  // 按 group 分组
  const groups = new Map<string, TopoNode[]>();
  for (const node of nodes) {
    const g = node.group || 'app';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(node);
  }

  // 排序分组
  const sortedGroups = Array.from(groups.entries()).sort((a, b) => {
    const oa = GROUP_CONFIG[a[0]]?.order ?? 99;
    const ob = GROUP_CONFIG[b[0]]?.order ?? 99;
    return oa - ob;
  });

  // 网格布局：3 列
  const cols = 3;
  const rows = Math.ceil(sortedGroups.length / cols);
  const cellW = (width - 80) / cols;
  const cellH = Math.max(200, (height - 100) / rows);
  const padX = 50;
  const padY = 50;

  const positions = new Map<number, { x: number; y: number }>();
  const groupBoxes: GroupBox[] = [];

  sortedGroups.forEach(([groupKey, groupNodes], idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    const boxX = padX + col * cellW;
    const boxY = padY + row * cellH;
    const config = GROUP_CONFIG[groupKey] || { label: groupKey, color: '#999', bgColor: 'rgba(0,0,0,0.03)', order: 99 };

    groupBoxes.push({
      key: groupKey,
      label: config.label,
      x: boxX,
      y: boxY,
      width: cellW - 20,
      height: cellH - 20,
      bgColor: config.bgColor,
    });

    // 在分组区域内排列节点（网格）
    const innerPad = 30;
    const availW = cellW - 20 - innerPad * 2;
    const availH = cellH - 20 - innerPad - 50; // 留出标题空间
    const innerCols = Math.min(groupNodes.length, Math.max(1, Math.floor(availW / 100)));
    const innerRows = Math.ceil(groupNodes.length / innerCols);
    const stepX = innerCols > 1 ? availW / (innerCols - 1 || 1) : 0;
    const stepY = innerRows > 1 ? availH / (innerRows - 1 || 1) : 0;

    groupNodes.forEach((node, ni) => {
      const ic = ni % innerCols;
      const ir = Math.floor(ni / innerCols);
      positions.set(node.id, {
        x: boxX + innerPad + (innerCols === 1 ? availW / 2 : ic * stepX),
        y: boxY + 50 + (innerRows === 1 ? availH / 2 : ir * stepY),
      });
    });
  });

  return { positions, groupBoxes };
};

interface GroupBox {
  key: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  bgColor: string;
}

/* ==================== 连线样式 ==================== */

const EDGE_STYLES: Record<string, { color: string; type: 'solid' | 'dashed'; width: number; label: string }> = {
  calls:      { color: '#1890ff', type: 'solid',  width: 2,   label: 'API 调用' },
  depends_on: { color: '#faad14', type: 'dashed', width: 1.5, label: '依赖' },
};

/* ==================== 组件 ==================== */

export default function Topology() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [loading, setLoading] = useState(false);
  const [layout, setLayout] = useState<LayoutMode>('grouped');
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const topoData = useRef<TopologyData | null>(null);

  /** 从后端加载拓扑数据 */
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/topology', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('请求失败');
      const data: TopologyData = await res.json();
      topoData.current = data;
      setStats({ nodes: data.nodes.length, edges: data.edges.length });
      renderChart(data, layout);
    } catch {
      message.error('加载拓扑数据失败');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  /** 渲染图表 */
  const renderChart = (data: TopologyData, mode: LayoutMode) => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const chart = chartInstance.current;
    const containerW = chartRef.current.clientWidth || 1200;
    const containerH = chartRef.current.clientHeight || 800;

    // 节点 ID → 名称映射
    const idMap = new Map<number, string>();
    data.nodes.forEach((n) => idMap.set(n.id, n.name));

    // 分组布局坐标
    const isGrouped = mode === 'grouped';
    const layoutResult = isGrouped
      ? computeGroupedPositions(data.nodes, containerW, containerH)
      : null;

    // 构建分类
    const categoryNames = Array.from(new Set(data.nodes.map((n) => n.group)));
    const categories = categoryNames.map((g) => ({
      name: GROUP_CONFIG[g]?.label || g,
      itemStyle: { color: GROUP_CONFIG[g]?.color || '#999' },
    }));

    // 构建节点
    const nodes = data.nodes.map((n) => {
      const config = GROUP_CONFIG[n.group] || { color: '#999', label: n.group };
      const pos = layoutResult?.positions.get(n.id);
      const statusColor = getStatusColor(n.status);

      return {
        id: String(n.id),
        name: shortName(n.name),
        symbolSize: 40,
        symbol: 'circle',
        ...(pos ? { x: pos.x, y: pos.y, fixed: true } : {}),
        itemStyle: {
          color: config.color,
          borderColor: statusColor,
          borderWidth: 3,
          shadowColor: 'rgba(0,0,0,0.1)',
          shadowBlur: 8,
        },
        label: {
          show: true,
          position: 'bottom' as const,
          fontSize: 11,
          color: '#555',
          overflow: 'truncate' as const,
          width: 90,
        },
        tooltip: {
          formatter:
            `<div style="font-weight:600;margin-bottom:4px">${n.name}</div>` +
            `<div>类型: ${config.label}</div>` +
            `<div>状态: <span style="color:${statusColor}">●</span> ${n.status}</div>` +
            `<div>主机: ${n.host || '—'}</div>`,
        },
        category: categoryNames.indexOf(n.group),
      };
    });

    // 构建边
    const edges = data.edges.map((e) => {
      const style = EDGE_STYLES[e.type] || EDGE_STYLES.depends_on;
      return {
        source: String(e.source),
        target: String(e.target),
        lineStyle: {
          color: style.color,
          type: style.type,
          width: style.width,
          curveness: 0.2,
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        tooltip: {
          formatter:
            `<b>${idMap.get(e.source) ?? e.source}</b> → <b>${idMap.get(e.target) ?? e.target}</b>` +
            `<br/>${style.label}: ${e.description}`,
        },
      };
    });

    // 分组背景矩形（仅分组模式）
    const graphicElements: any[] = [];
    if (isGrouped && layoutResult?.groupBoxes) {
      for (const box of layoutResult.groupBoxes) {
        // 背景
        graphicElements.push({
          type: 'rect',
          left: box.x,
          top: box.y,
          shape: { width: box.width, height: box.height, r: 8 },
          style: {
            fill: box.bgColor,
            stroke: 'rgba(0,0,0,0.06)',
            lineWidth: 1,
          },
          silent: true,
          z: -1,
        });
        // 标题
        graphicElements.push({
          type: 'text',
          left: box.x + 10,
          top: box.y + 10,
          style: {
            text: box.label,
            fontSize: 13,
            fontWeight: 'bold' as const,
            fill: '#666',
          },
          silent: true,
        });
      }
    }

    const option: echarts.EChartsOption = {
      tooltip: { trigger: 'item', confine: true },
      legend: {
        data: categories.map((c) => c.name),
        orient: 'horizontal',
        bottom: 10,
        textStyle: { fontSize: 12 },
        itemWidth: 14,
        itemHeight: 14,
      },
      graphic: graphicElements,
      animationDuration: 500,
      series: [
        {
          type: 'graph',
          layout: isGrouped ? 'none' : 'force',
          roam: true,
          draggable: true,
          zoom: 1,
          categories,
          data: nodes,
          links: edges,
          ...(mode === 'force'
            ? {
                force: {
                  repulsion: 400,
                  edgeLength: [150, 300],
                  gravity: 0.08,
                  layoutAnimation: true,
                },
              }
            : {}),
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 3 },
            itemStyle: {
              shadowBlur: 12,
              shadowColor: 'rgba(0,0,0,0.3)',
            },
          },
          lineStyle: {
            curveness: 0.2,
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
        <Space>
          <Title level={4} style={{ margin: 0 }}>服务拓扑</Title>
          <Tag color="blue">{stats.nodes} 个服务</Tag>
          <Tag color="orange">{stats.edges} 条依赖</Tag>
        </Space>
        <Space>
          <Radio.Group
            value={layout}
            onChange={(e) => handleLayoutChange(e.target.value)}
            optionType="button"
            buttonStyle="solid"
            size="small"
          >
            <Radio.Button value="grouped">
              <ApartmentOutlined /> 分组布局
            </Radio.Button>
            <Radio.Button value="force">
              <NodeIndexOutlined /> 力导向
            </Radio.Button>
          </Radio.Group>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>
      <div style={{ marginBottom: 8 }}>
        <Space size={16}>
          <span style={{ fontSize: 12, color: '#999' }}>
            连线: <span style={{ color: '#1890ff' }}>━</span> API 调用　
            <span style={{ color: '#faad14' }}>╌╌</span> 依赖
          </span>
          <span style={{ fontSize: 12, color: '#999' }}>
            边框: <span style={{ color: '#52c41a' }}>●</span> 正常　
            <span style={{ color: '#ff4d4f' }}>●</span> 异常　
            <span style={{ color: '#d9d9d9' }}>●</span> 未知
          </span>
        </Space>
      </div>
      <Spin spinning={loading}>
        <div
          ref={chartRef}
          style={{
            width: '100%',
            height: 'calc(100vh - 240px)',
            minHeight: 600,
            background: '#fafafa',
            borderRadius: 8,
            border: '1px solid #f0f0f0',
          }}
        />
      </Spin>
    </div>
  );
}
