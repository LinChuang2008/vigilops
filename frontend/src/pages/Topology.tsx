/**
 * 服务拓扑图页面
 *
 * 支持：
 * 1. 自动分组布局 / 力导向布局切换
 * 2. 拖拽节点 + 保存自定义布局
 * 3. 编辑模式：点击两个节点创建依赖，点击连线删除
 * 4. AI 智能推荐依赖关系
 * 5. 节点状态指示（边框色）、悬停高亮关联
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Typography, Button, Spin, message, Radio, Space, Tag, Modal,
  Tooltip, Drawer, List, Popconfirm, Select,
} from 'antd';
import {
  ReloadOutlined, ApartmentOutlined, NodeIndexOutlined,
  EditOutlined, SaveOutlined, UndoOutlined, RobotOutlined,
  PlusOutlined, DeleteOutlined, CheckOutlined, CloseOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';

const { Title, Text, Paragraph } = Typography;

/* ==================== 类型 ==================== */

interface TopoNode {
  id: number; name: string; type: string; status: string;
  host: string; host_id?: number; group: string;
}
interface TopoEdge {
  source: number; target: number; type: string;
  description: string; id?: number; manual?: boolean;
}
interface TopologyData {
  nodes: TopoNode[]; edges: TopoEdge[];
  hosts?: { id: number; name: string }[];
  saved_positions?: Record<string, { x: number; y: number }> | null;
  has_custom_deps?: boolean;
}
interface AISuggestion {
  source: number; target: number; type: string; description: string;
}

type LayoutMode = 'grouped' | 'force';

/* ==================== 分组配置 ==================== */

const GROUP_CONFIG: Record<string, { label: string; color: string; bgColor: string; order: number }> = {
  web:      { label: '🌐 前端服务', color: '#FFB800', bgColor: 'rgba(255,184,0,0.08)',   order: 0 },
  api:      { label: '⚙️ 后端服务', color: '#FF7F50', bgColor: 'rgba(255,127,80,0.08)',  order: 1 },
  app:      { label: '📦 业务应用', color: '#4FC3F7', bgColor: 'rgba(79,195,247,0.08)',  order: 2 },
  registry: { label: '🔍 注册中心', color: '#AB47BC', bgColor: 'rgba(171,71,188,0.08)',  order: 3 },
  mq:       { label: '📨 消息队列', color: '#00CED1', bgColor: 'rgba(0,206,209,0.08)',   order: 4 },
  olap:     { label: '📊 分析引擎', color: '#FF8A65', bgColor: 'rgba(255,138,101,0.08)', order: 5 },
  database: { label: '🗄️ 数据库',  color: '#7B68EE', bgColor: 'rgba(123,104,238,0.08)', order: 6 },
  cache:    { label: '⚡ 缓存',    color: '#9ACD32', bgColor: 'rgba(154,205,50,0.08)',   order: 7 },
};

const STATUS_COLORS: Record<string, string> = {
  up: '#52c41a', running: '#52c41a', healthy: '#52c41a',
  down: '#ff4d4f', stopped: '#ff4d4f',
  warning: '#faad14', unknown: '#d9d9d9',
};
const getStatusColor = (s: string) => STATUS_COLORS[s?.toLowerCase()] || STATUS_COLORS.unknown;
const shortName = (name: string) => {
  let s = name.replace(/\s*\(:\d+\)/, '').replace(/-1$/, '');
  return s.length > 18 ? s.substring(0, 16) + '…' : s;
};

const EDGE_STYLES: Record<string, { color: string; type: 'solid' | 'dashed'; width: number; label: string }> = {
  calls:      { color: '#1890ff', type: 'solid',  width: 2,   label: 'API 调用' },
  depends_on: { color: '#faad14', type: 'dashed', width: 1.5, label: '依赖' },
};

/* ==================== 分组布局 ==================== */

interface GroupBox { key: string; label: string; x: number; y: number; width: number; height: number; bgColor: string; }

const computeGroupedPositions = (nodes: TopoNode[], w: number, h: number) => {
  const groups = new Map<string, TopoNode[]>();
  for (const n of nodes) {
    const g = n.group || 'app';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(n);
  }
  const sorted = Array.from(groups.entries()).sort((a, b) =>
    (GROUP_CONFIG[a[0]]?.order ?? 99) - (GROUP_CONFIG[b[0]]?.order ?? 99));

  const cols = 3, rows = Math.ceil(sorted.length / cols);
  const cellW = (w - 80) / cols, cellH = Math.max(200, (h - 100) / rows);
  const positions = new Map<number, { x: number; y: number }>();
  const boxes: GroupBox[] = [];

  sorted.forEach(([key, items], idx) => {
    const col = idx % cols, row = Math.floor(idx / cols);
    const bx = 50 + col * cellW, by = 50 + row * cellH;
    const cfg = GROUP_CONFIG[key] || { label: key, color: '#999', bgColor: 'rgba(0,0,0,0.03)', order: 99 };
    boxes.push({ key, label: cfg.label, x: bx, y: by, width: cellW - 20, height: cellH - 20, bgColor: cfg.bgColor });

    const pad = 30, availW = cellW - 20 - pad * 2, availH = cellH - 20 - pad - 50;
    const ic = Math.min(items.length, Math.max(1, Math.floor(availW / 100)));
    const ir = Math.ceil(items.length / ic);
    const sx = ic > 1 ? availW / (ic - 1 || 1) : 0;
    const sy = ir > 1 ? availH / (ir - 1 || 1) : 0;

    items.forEach((n, ni) => {
      positions.set(n.id, {
        x: bx + pad + (ic === 1 ? availW / 2 : (ni % ic) * sx),
        y: by + 50 + (ir === 1 ? availH / 2 : Math.floor(ni / ic) * sy),
      });
    });
  });
  return { positions, groupBoxes: boxes };
};

/* ==================== 组件 ==================== */

export default function Topology() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [loading, setLoading] = useState(false);
  const [layout, setLayout] = useState<LayoutMode>('grouped');
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const topoData = useRef<TopologyData | null>(null);

  // 编辑模式（用 ref 同步最新值给 ECharts 闭包）
  const [editMode, setEditMode] = useState(false);
  const [connecting, setConnecting] = useState<number | null>(null);
  const [depType, setDepType] = useState<string>('depends_on');
  const editModeRef = useRef(false);
  const connectingRef = useRef<number | null>(null);
  const depTypeRef = useRef('depends_on');

  // AI 推荐
  const [aiLoading, setAiLoading] = useState(false);
  const [aiDrawerOpen, setAiDrawerOpen] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [aiMessage, setAiMessage] = useState('');

  // 节点名映射
  const nodeNameMap = useRef<Map<number, string>>(new Map());

  // 同步 state → ref（确保 ECharts 闭包读到最新值）
  useEffect(() => { editModeRef.current = editMode; }, [editMode]);
  useEffect(() => { connectingRef.current = connecting; }, [connecting]);
  useEffect(() => { depTypeRef.current = depType; }, [depType]);

  /** 获取 token */
  const getToken = () => localStorage.getItem('access_token') || '';

  /** 加载数据 */
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/topology', {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error();
      const data: TopologyData = await res.json();
      topoData.current = data;
      setStats({ nodes: data.nodes.length, edges: data.edges.length });

      const nameMap = new Map<number, string>();
      data.nodes.forEach(n => nameMap.set(n.id, n.name));
      nodeNameMap.current = nameMap;

      renderChart(data, layout);
    } catch {
      message.error('加载拓扑数据失败');
    } finally {
      setLoading(false);
    }
  }, [layout]); // eslint-disable-line

  // 记录拖拽后的节点位置
  const draggedPositions = useRef<Record<string, { x: number; y: number }>>({});

  /** 保存布局 */
  const saveLayout = async () => {
    const chart = chartInstance.current;
    if (!chart || !topoData.current) return;

    // 合并：初始位置 + 拖拽修改的位置
    const option = chart.getOption() as any;
    const seriesData = option?.series?.[0]?.data;
    if (!seriesData) return;

    const positions: Record<string, { x: number; y: number }> = {};
    for (const node of seriesData) {
      if (node.x !== undefined && node.y !== undefined) {
        positions[node.id] = { x: node.x, y: node.y };
      }
    }
    // 覆盖拖拽过的位置
    Object.assign(positions, draggedPositions.current);

    try {
      const res = await fetch('/api/v1/topology/layout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions }),
      });
      if (!res.ok) throw new Error();
      message.success('布局已保存');
    } catch {
      message.error('保存布局失败');
    }
  };

  /** 重置布局 */
  const resetLayout = async () => {
    try {
      await fetch('/api/v1/topology/layout', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      message.success('布局已重置');
      fetchData();
    } catch {
      message.error('重置失败');
    }
  };

  /** 添加依赖 */
  const addDependency = async (source: number, target: number) => {
    try {
      const res = await fetch('/api/v1/topology/dependencies', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_service_id: source,
          target_service_id: target,
          dependency_type: depTypeRef.current,
          description: depTypeRef.current === 'calls' ? 'API 调用（手动添加）' : '依赖关系（手动添加）',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || '添加失败');
      }
      message.success(`已添加: ${nodeNameMap.current.get(source)} → ${nodeNameMap.current.get(target)}`);
      fetchData();
    } catch (e: any) {
      message.error(e.message || '添加依赖失败');
    }
  };

  /** 删除依赖 */
  const deleteDependency = async (depId: number) => {
    try {
      const res = await fetch(`/api/v1/topology/dependencies/${depId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error();
      message.success('依赖已删除');
      fetchData();
    } catch {
      message.error('删除失败');
    }
  };

  /** 清空所有自定义依赖 */
  const clearAllDeps = async () => {
    try {
      const res = await fetch('/api/v1/topology/dependencies', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error();
      message.success('已清空自定义依赖，回退到自动推断');
      fetchData();
    } catch {
      message.error('清空失败');
    }
  };

  /** AI 推荐 */
  const requestAISuggest = async () => {
    setAiLoading(true);
    setAiDrawerOpen(true);
    try {
      const res = await fetch('/api/v1/topology/ai-suggest', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'AI 分析失败');
      }
      const data = await res.json();
      setAiSuggestions(data.suggestions || []);
      setAiMessage(data.message || '');
    } catch (e: any) {
      message.error(e.message || 'AI 分析失败');
    } finally {
      setAiLoading(false);
    }
  };

  /** 应用单条 AI 建议 */
  const applyOneSuggestion = async (s: AISuggestion) => {
    try {
      const res = await fetch('/api/v1/topology/dependencies', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_service_id: s.source,
          target_service_id: s.target,
          dependency_type: s.type,
          description: s.description,
        }),
      });
      if (!res.ok) throw new Error();
      message.success('已应用');
      // 从列表移除
      setAiSuggestions(prev => prev.filter(x => !(x.source === s.source && x.target === s.target)));
      fetchData();
    } catch {
      message.error('应用失败');
    }
  };

  /** 应用全部 AI 建议 */
  const applyAllSuggestions = async () => {
    try {
      const body = aiSuggestions.map(s => ({
        source_service_id: s.source,
        target_service_id: s.target,
        dependency_type: s.type,
        description: s.description,
      }));
      const res = await fetch('/api/v1/topology/ai-suggest/apply', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      message.success(`已应用 ${data.created} 条依赖`);
      setAiSuggestions([]);
      setAiDrawerOpen(false);
      fetchData();
    } catch {
      message.error('批量应用失败');
    }
  };

  /** 渲染图表 */
  const renderChart = (data: TopologyData, mode: LayoutMode) => {
    if (!chartRef.current) return;
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }
    const chart = chartInstance.current;
    const cw = chartRef.current.clientWidth || 1200;
    const ch = chartRef.current.clientHeight || 800;

    const idMap = new Map<number, string>();
    data.nodes.forEach(n => idMap.set(n.id, n.name));

    const isGrouped = mode === 'grouped';
    const autoLayout = isGrouped ? computeGroupedPositions(data.nodes, cw, ch) : null;

    // 使用保存的位置 > 自动计算
    const savedPos = data.saved_positions;

    const categoryNames = Array.from(new Set(data.nodes.map(n => n.group)));
    const categories = categoryNames.map(g => ({
      name: GROUP_CONFIG[g]?.label || g,
      itemStyle: { color: GROUP_CONFIG[g]?.color || '#999' },
    }));

    const nodes = data.nodes.map(n => {
      const cfg = GROUP_CONFIG[n.group] || { color: '#999', label: n.group };
      // 优先用保存位置，其次自动计算
      const sp = savedPos?.[String(n.id)];
      const ap = autoLayout?.positions.get(n.id);
      const pos = sp || ap;

      return {
        id: String(n.id),
        name: shortName(n.name),
        symbolSize: 40,
        symbol: 'circle',
        ...(pos ? { x: pos.x, y: pos.y, fixed: isGrouped } : {}),
        itemStyle: {
          color: cfg.color, borderColor: getStatusColor(n.status),
          borderWidth: 3, shadowColor: 'rgba(0,0,0,0.1)', shadowBlur: 8,
        },
        label: { show: true, position: 'bottom' as const, fontSize: 11, color: '#555' },
        tooltip: {
          formatter:
            `<div style="font-weight:600;margin-bottom:4px">${n.name}</div>` +
            `<div>类型: ${cfg.label}</div>` +
            `<div>状态: <span style="color:${getStatusColor(n.status)}">●</span> ${n.status}</div>` +
            `<div>主机: ${n.host || '—'}</div>` +
            (editMode ? '<div style="color:#1890ff;margin-top:4px">💡 点击选中此节点创建连线</div>' : ''),
        },
        category: categoryNames.indexOf(n.group),
      };
    });

    const edges = data.edges.map(e => {
      const style = EDGE_STYLES[e.type] || EDGE_STYLES.depends_on;
      return {
        source: String(e.source), target: String(e.target),
        lineStyle: { color: style.color, type: style.type, width: style.width, curveness: 0.2 },
        edgeSymbol: ['none', 'arrow'] as [string, string],
        edgeSymbolSize: [0, 8],
        tooltip: {
          formatter:
            `<b>${idMap.get(e.source) ?? e.source}</b> → <b>${idMap.get(e.target) ?? e.target}</b>` +
            `<br/>${style.label}: ${e.description}` +
            (e.manual && e.id ? `<br/><span style="color:#ff4d4f">🗑️ 编辑模式下点击可删除 (ID:${e.id})</span>` : ''),
        },
        // 存储 edge 元数据用于点击事件
        _depId: e.id,
        _manual: e.manual,
      };
    });

    // 分组背景
    const graphics: any[] = [];
    if (isGrouped && !savedPos && autoLayout?.groupBoxes) {
      for (const box of autoLayout.groupBoxes) {
        graphics.push({
          type: 'rect', left: box.x, top: box.y, z: -1, silent: true,
          shape: { width: box.width, height: box.height, r: 8 },
          style: { fill: box.bgColor, stroke: 'rgba(0,0,0,0.06)', lineWidth: 1 },
        });
        graphics.push({
          type: 'text', left: box.x + 10, top: box.y + 10, silent: true,
          style: { text: box.label, fontSize: 13, fontWeight: 'bold' as const, fill: '#666' },
        });
      }
    }

    const option: echarts.EChartsOption = {
      tooltip: { trigger: 'item', confine: true },
      legend: {
        data: categories.map(c => c.name), orient: 'horizontal', bottom: 10,
        textStyle: { fontSize: 12 }, itemWidth: 14, itemHeight: 14,
      },
      graphic: graphics,
      animationDuration: 500,
      series: [{
        type: 'graph',
        layout: isGrouped ? 'none' : 'force',
        roam: true,
        draggable: true,
        zoom: 1,
        categories,
        data: nodes,
        links: edges as any,
        ...(mode === 'force' ? {
          force: { repulsion: 400, edgeLength: [150, 300], gravity: 0.08, layoutAnimation: true },
        } : {}),
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3 },
          itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.3)' },
        },
        lineStyle: { curveness: 0.2 },
      }],
    };

    chart.setOption(option, true);
    chart.resize();

    // 注册拖拽结束事件，记录新位置
    chart.off('mouseup');
    chart.on('mouseup', (params: any) => {
      if (params.dataType === 'node' && params.event) {
        // 通过 convertFromPixel 获取拖拽后的逻辑坐标
        const point = chart.convertFromPixel({ seriesIndex: 0 }, [params.event.offsetX, params.event.offsetY]);
        if (point) {
          draggedPositions.current[params.data.id] = { x: point[0], y: point[1] };
        }
      }
    });

    // 注册点击事件（通过 ref 读取最新 state）
    chart.off('click');
    chart.on('click', (params: any) => {
      if (!editModeRef.current) return;

      if (params.dataType === 'node') {
        const nodeId = parseInt(params.data.id);
        const currentConnecting = connectingRef.current;
        if (currentConnecting === null) {
          setConnecting(nodeId);
          message.info(`已选中 "${idMap.get(nodeId)}"，点击目标节点完成连线`);
        } else if (currentConnecting === nodeId) {
          setConnecting(null);
          message.info('已取消选择');
        } else {
          addDependency(currentConnecting, nodeId);
          setConnecting(null);
        }
      } else if (params.dataType === 'edge') {
        const depId = params.data?._depId;
        const isManual = params.data?._manual;
        if (depId && isManual) {
          Modal.confirm({
            title: '删除依赖关系？',
            content: `${params.data.source} → ${params.data.target}`,
            okText: '删除',
            okType: 'danger',
            onOk: () => deleteDependency(depId),
          });
        }
      }
    });
  };

  const handleLayoutChange = (mode: LayoutMode) => {
    setLayout(mode);
    if (topoData.current) renderChart(topoData.current, mode);
  };

  useEffect(() => {
    fetchData();
    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); chartInstance.current?.dispose(); };
  }, []); // eslint-disable-line

  return (
    <div>
      {/* 标题栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>服务拓扑</Title>
          <Tag color="blue">{stats.nodes} 个服务</Tag>
          <Tag color="orange">{stats.edges} 条依赖</Tag>
          {topoData.current?.has_custom_deps && <Tag color="green">自定义依赖</Tag>}
        </Space>
        <Space>
          <Radio.Group value={layout} onChange={e => handleLayoutChange(e.target.value)}
            optionType="button" buttonStyle="solid" size="small">
            <Radio.Button value="grouped"><ApartmentOutlined /> 分组</Radio.Button>
            <Radio.Button value="force"><NodeIndexOutlined /> 力导向</Radio.Button>
          </Radio.Group>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
        </Space>
      </div>

      {/* 工具栏 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 12, padding: '8px 12px', background: editMode ? '#fff7e6' : '#fafafa',
        borderRadius: 6, border: `1px solid ${editMode ? '#ffd591' : '#f0f0f0'}`,
      }}>
        <Space>
          {/* 编辑模式切换 */}
          <Button
            type={editMode ? 'primary' : 'default'}
            icon={editMode ? <CheckOutlined /> : <EditOutlined />}
            onClick={() => { setEditMode(!editMode); setConnecting(null); }}
            danger={editMode}
          >
            {editMode ? '退出编辑' : '编辑模式'}
          </Button>

          {editMode && (
            <>
              <Select value={depType} onChange={setDepType} size="small" style={{ width: 130 }}
                options={[
                  { label: '━ API 调用', value: 'calls' },
                  { label: '╌ 依赖关系', value: 'depends_on' },
                ]}
              />
              {connecting && (
                <Tag color="processing" icon={<PlusOutlined />}>
                  已选: {shortName(nodeNameMap.current.get(connecting) || '')} → 点击目标节点
                  <CloseOutlined style={{ marginLeft: 4, cursor: 'pointer' }} onClick={() => setConnecting(null)} />
                </Tag>
              )}
              <Popconfirm title="清空所有自定义依赖？" onConfirm={clearAllDeps} okText="清空" okType="danger">
                <Button size="small" danger icon={<DeleteOutlined />}>清空依赖</Button>
              </Popconfirm>
            </>
          )}
        </Space>

        <Space>
          {/* AI 推荐 */}
          <Tooltip title="AI 分析服务关系，智能推荐依赖">
            <Button icon={<RobotOutlined />} onClick={requestAISuggest} loading={aiLoading}>
              AI 推荐
            </Button>
          </Tooltip>

          {/* 布局操作 */}
          <Tooltip title="保存当前节点位置">
            <Button icon={<SaveOutlined />} onClick={saveLayout}>保存布局</Button>
          </Tooltip>
          <Tooltip title="重置为自动布局">
            <Button icon={<UndoOutlined />} onClick={resetLayout}>重置布局</Button>
          </Tooltip>
        </Space>
      </div>

      {/* 图例 */}
      <div style={{ marginBottom: 8 }}>
        <Space size={16}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            连线: <span style={{ color: '#1890ff' }}>━</span> API 调用　
            <span style={{ color: '#faad14' }}>╌╌</span> 依赖
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            边框: <span style={{ color: '#52c41a' }}>●</span> 正常　
            <span style={{ color: '#ff4d4f' }}>●</span> 异常　
            <span style={{ color: '#d9d9d9' }}>●</span> 未知
          </Text>
          {editMode && (
            <Text type="warning" style={{ fontSize: 12 }}>
              ✏️ 编辑模式：点击节点创建连线，点击自定义连线删除
            </Text>
          )}
        </Space>
      </div>

      {/* 图表 */}
      <Spin spinning={loading}>
        <div ref={chartRef} style={{
          width: '100%', height: 'calc(100vh - 280px)', minHeight: 550,
          background: '#fafafa', borderRadius: 8, border: '1px solid #f0f0f0',
        }} />
      </Spin>

      {/* AI 推荐抽屉 */}
      <Drawer
        title={<Space><RobotOutlined /> AI 智能推荐</Space>}
        open={aiDrawerOpen}
        onClose={() => setAiDrawerOpen(false)}
        width={480}
        extra={
          aiSuggestions.length > 0 ? (
            <Button type="primary" icon={<CheckOutlined />} onClick={applyAllSuggestions}>
              全部应用 ({aiSuggestions.length})
            </Button>
          ) : null
        }
      >
        {aiLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <Paragraph style={{ marginTop: 16 }}>AI 正在分析服务关系...</Paragraph>
          </div>
        ) : (
          <>
            {aiMessage && <Paragraph type="secondary"><BulbOutlined /> {aiMessage}</Paragraph>}
            {aiSuggestions.length === 0 ? (
              <Paragraph type="secondary">暂无新的推荐依赖关系</Paragraph>
            ) : (
              <List
                dataSource={aiSuggestions}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button type="link" icon={<CheckOutlined />} onClick={() => applyOneSuggestion(item)}>
                        应用
                      </Button>,
                      <Button type="link" danger icon={<CloseOutlined />}
                        onClick={() => setAiSuggestions(prev => prev.filter(x => x !== item))}>
                        忽略
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Text strong>{shortName(nodeNameMap.current.get(item.source) || String(item.source))}</Text>
                          <Text type="secondary">→</Text>
                          <Text strong>{shortName(nodeNameMap.current.get(item.target) || String(item.target))}</Text>
                          <Tag color={item.type === 'calls' ? 'blue' : 'orange'} style={{ marginLeft: 4 }}>
                            {item.type === 'calls' ? 'API 调用' : '依赖'}
                          </Tag>
                        </Space>
                      }
                      description={item.description}
                    />
                  </List.Item>
                )}
              />
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}
