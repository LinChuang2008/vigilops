/**
 * 服务拓扑图页面
 *
 * 图表展示 + 侧面板编辑：
 * - 左侧：ECharts 拓扑图（拖拽节点 + 保存布局）
 * - 右侧面板：依赖关系列表、添加/删除依赖、AI 推荐
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Typography, Button, Spin, message, Radio, Space, Tag,
  Drawer, List, Select, Card, Divider, Empty, Popconfirm, Tooltip,
} from 'antd';
import {
  ReloadOutlined, ApartmentOutlined, NodeIndexOutlined,
  EditOutlined, SaveOutlined, UndoOutlined, RobotOutlined,
  PlusOutlined, DeleteOutlined, CheckOutlined, CloseOutlined,
  BulbOutlined, UnorderedListOutlined,
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
  saved_positions?: Record<string, { x: number; y: number }> | null;
  has_custom_deps?: boolean;
}
interface AISuggestion {
  source: number; target: number; type: string; description: string;
}

type LayoutMode = 'grouped' | 'force';

/* ==================== 配置 ==================== */

const GROUP_CONFIG: Record<string, { label: string; color: string; bgColor: string; order: number; stage: number }> = {
  web:      { label: '🌐 前端',    color: '#FFB800', bgColor: 'rgba(255,184,0,0.08)',   order: 0, stage: 0 },
  api:      { label: '⚙️ 后端',    color: '#FF7F50', bgColor: 'rgba(255,127,80,0.08)',  order: 1, stage: 1 },
  app:      { label: '📦 业务',    color: '#4FC3F7', bgColor: 'rgba(79,195,247,0.08)',  order: 2, stage: 1 },
  registry: { label: '🔍 注册中心', color: '#AB47BC', bgColor: 'rgba(171,71,188,0.08)',  order: 3, stage: 2 },
  mq:       { label: '📨 消息队列', color: '#00CED1', bgColor: 'rgba(0,206,209,0.08)',   order: 4, stage: 2 },
  olap:     { label: '📊 分析引擎', color: '#FF8A65', bgColor: 'rgba(255,138,101,0.08)', order: 5, stage: 2 },
  database: { label: '🗄️ 数据库',  color: '#7B68EE', bgColor: 'rgba(123,104,238,0.08)', order: 6, stage: 3 },
  cache:    { label: '⚡ 缓存',    color: '#9ACD32', bgColor: 'rgba(154,205,50,0.08)',   order: 7, stage: 3 },
};

/** 管道阶段定义（从左到右） */
const PIPELINE_STAGES = [
  { key: 0, label: '接入层', color: '#FFB800' },
  { key: 1, label: '应用层', color: '#FF7F50' },
  { key: 2, label: '中间件', color: '#AB47BC' },
  { key: 3, label: '数据层', color: '#7B68EE' },
];

const STATUS_COLORS: Record<string, string> = {
  up: '#52c41a', running: '#52c41a', healthy: '#52c41a',
  down: '#ff4d4f', stopped: '#ff4d4f', warning: '#faad14', unknown: '#d9d9d9',
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

interface StageBox { stageIdx: number; label: string; x: number; y: number; width: number; height: number; color: string; }

/**
 * 管道布局：从左到右 4 个阶段，每个阶段内节点纵向排列。
 * 阶段之间用箭头连接管道和连线。
 */
const computePipelinePositions = (nodes: TopoNode[], w: number, h: number) => {
  // 按 stage 分组
  const stageBuckets: TopoNode[][] = [[], [], [], []];
  for (const n of nodes) {
    const cfg = GROUP_CONFIG[n.group];
    const stage = cfg?.stage ?? 1;
    stageBuckets[stage].push(n);
  }

  const stageCount = PIPELINE_STAGES.length;
  const stageWidth = (w - 60) / stageCount;
  const padTop = 70;     // 留给阶段标题
  const padBottom = 30;
  const availH = h - padTop - padBottom;
  const positions = new Map<number, { x: number; y: number }>();
  const stageBoxes: StageBox[] = [];

  stageBuckets.forEach((bucket, si) => {
    const stageCfg = PIPELINE_STAGES[si];
    const stageX = 30 + si * stageWidth;

    stageBoxes.push({
      stageIdx: si,
      label: stageCfg.label,
      x: stageX,
      y: 10,
      width: stageWidth - 10,
      height: h - 20,
      color: stageCfg.color,
    });

    if (bucket.length === 0) return;

    // 节点在阶段内纵向居中排列
    const spacing = Math.min(80, availH / (bucket.length + 1));
    const totalH = spacing * (bucket.length - 1);
    const startY = padTop + (availH - totalH) / 2;
    const centerX = stageX + (stageWidth - 10) / 2;

    bucket.forEach((node, ni) => {
      positions.set(node.id, {
        x: centerX,
        y: startY + ni * spacing,
      });
    });
  });

  return { positions, stageBoxes };
};

/* ==================== 组件 ==================== */

export default function Topology() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [loading, setLoading] = useState(false);
  const [layout, setLayout] = useState<LayoutMode>('grouped');
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const topoData = useRef<TopologyData | null>(null);

  // 编辑面板
  const [panelOpen, setPanelOpen] = useState(false);
  const [addSource, setAddSource] = useState<number | undefined>();
  const [addTarget, setAddTarget] = useState<number | undefined>();
  const [addType, setAddType] = useState<string>('depends_on');

  // AI 推荐
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [aiMessage, setAiMessage] = useState('');
  const [aiTab, setAiTab] = useState<'deps' | 'ai'>('deps');

  // 节点名映射
  const nodeNameMap = useRef<Map<number, string>>(new Map());

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
    } finally { setLoading(false); }
  }, [layout]); // eslint-disable-line

  /** 保存布局 */
  const saveLayout = async () => {
    const chart = chartInstance.current;
    if (!chart || !topoData.current) return;
    const option = chart.getOption() as any;
    const seriesData = option?.series?.[0]?.data;
    if (!seriesData) return;

    const positions: Record<string, { x: number; y: number }> = {};
    for (const node of seriesData) {
      if (node.x !== undefined && node.y !== undefined) {
        positions[node.id] = { x: node.x, y: node.y };
      }
    }
    try {
      const res = await fetch('/api/v1/topology/layout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ positions }),
      });
      if (!res.ok) throw new Error();
      message.success('布局已保存');
    } catch { message.error('保存布局失败'); }
  };

  /** 重置布局 */
  const resetLayout = async () => {
    try {
      await fetch('/api/v1/topology/layout', { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } });
      message.success('布局已重置');
      fetchData();
    } catch { message.error('重置失败'); }
  };

  /** 添加依赖 */
  const addDependency = async () => {
    if (!addSource || !addTarget) { message.warning('请选择源服务和目标服务'); return; }
    if (addSource === addTarget) { message.warning('不能连接自己'); return; }
    try {
      const res = await fetch('/api/v1/topology/dependencies', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_service_id: addSource,
          target_service_id: addTarget,
          dependency_type: addType,
          description: addType === 'calls' ? 'API 调用（手动添加）' : '依赖关系（手动添加）',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || '添加失败');
      }
      message.success('依赖已添加');
      setAddSource(undefined);
      setAddTarget(undefined);
      fetchData();
    } catch (e: any) { message.error(e.message || '添加失败'); }
  };

  /** 删除依赖 */
  const deleteDependency = async (depId: number) => {
    try {
      await fetch(`/api/v1/topology/dependencies/${depId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
      });
      message.success('已删除');
      fetchData();
    } catch { message.error('删除失败'); }
  };

  /** 清空依赖 */
  const clearAllDeps = async () => {
    try {
      await fetch('/api/v1/topology/dependencies', {
        method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
      });
      message.success('已清空，回退到自动推断');
      fetchData();
    } catch { message.error('清空失败'); }
  };

  /** AI 推荐 */
  const requestAISuggest = async () => {
    setAiLoading(true);
    setAiTab('ai');
    try {
      const res = await fetch('/api/v1/topology/ai-suggest', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'AI 分析失败');
      const data = await res.json();
      setAiSuggestions(data.suggestions || []);
      setAiMessage(data.message || '');
    } catch (e: any) { message.error(e.message); }
    finally { setAiLoading(false); }
  };

  /** 应用单条 AI 建议 */
  const applyOneSuggestion = async (s: AISuggestion) => {
    try {
      const res = await fetch('/api/v1/topology/dependencies', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_service_id: s.source, target_service_id: s.target, dependency_type: s.type, description: s.description }),
      });
      if (!res.ok) throw new Error();
      message.success('已应用');
      setAiSuggestions(prev => prev.filter(x => !(x.source === s.source && x.target === s.target)));
      fetchData();
    } catch { message.error('应用失败'); }
  };

  /** 应用全部 AI 建议 */
  const applyAllSuggestions = async () => {
    const body = aiSuggestions.map(s => ({
      source_service_id: s.source, target_service_id: s.target, dependency_type: s.type, description: s.description,
    }));
    try {
      const res = await fetch('/api/v1/topology/ai-suggest/apply', {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      message.success(`已应用 ${data.created} 条`);
      setAiSuggestions([]);
      fetchData();
    } catch { message.error('批量应用失败'); }
  };

  /** 渲染图表 */
  const renderChart = (data: TopologyData, mode: LayoutMode) => {
    if (!chartRef.current) return;
    if (!chartInstance.current) chartInstance.current = echarts.init(chartRef.current);
    const chart = chartInstance.current;
    const cw = chartRef.current.clientWidth || 1200;
    const ch = chartRef.current.clientHeight || 800;

    const idMap = new Map<number, string>();
    data.nodes.forEach(n => idMap.set(n.id, n.name));

    const isPipeline = mode === 'grouped';
    const autoLayout = isPipeline ? computePipelinePositions(data.nodes, cw, ch) : null;
    const savedPos = data.saved_positions;

    const categoryNames = Array.from(new Set(data.nodes.map(n => n.group)));
    const categories = categoryNames.map(g => ({
      name: GROUP_CONFIG[g]?.label || g, itemStyle: { color: GROUP_CONFIG[g]?.color || '#999' },
    }));

    const nodes = data.nodes.map(n => {
      const cfg = GROUP_CONFIG[n.group] || { color: '#999' };
      const sp = savedPos?.[String(n.id)];
      const ap = autoLayout?.positions.get(n.id);
      const pos = sp || ap;
      return {
        id: String(n.id), name: shortName(n.name), symbolSize: 40, symbol: 'circle',
        ...(pos ? { x: pos.x, y: pos.y, fixed: isPipeline } : {}),
        itemStyle: { color: cfg.color, borderColor: getStatusColor(n.status), borderWidth: 3, shadowColor: 'rgba(0,0,0,0.1)', shadowBlur: 8 },
        label: { show: true, position: 'bottom' as const, fontSize: 11, color: '#555' },
        tooltip: {
          formatter: `<div style="font-weight:600;margin-bottom:4px">${n.name}</div>` +
            `<div>类型: ${GROUP_CONFIG[n.group]?.label || n.group}</div>` +
            `<div>状态: <span style="color:${getStatusColor(n.status)}">●</span> ${n.status}</div>` +
            `<div>主机: ${n.host || '—'}</div>`,
        },
        category: categoryNames.indexOf(n.group),
      };
    });

    const edges = data.edges.map(e => {
      const style = EDGE_STYLES[e.type] || EDGE_STYLES.depends_on;
      return {
        source: String(e.source), target: String(e.target),
        lineStyle: { color: style.color, type: style.type, width: style.width, curveness: 0.2 },
        edgeSymbol: ['none', 'arrow'] as [string, string], edgeSymbolSize: [0, 8],
        tooltip: {
          formatter: `<b>${idMap.get(e.source) ?? e.source}</b> → <b>${idMap.get(e.target) ?? e.target}</b><br/>${style.label}: ${e.description}`,
        },
      };
    });

    const graphics: any[] = [];
    if (isPipeline && autoLayout?.stageBoxes) {
      const stageBoxes = autoLayout.stageBoxes;
      stageBoxes.forEach((box, i) => {
        // 阶段背景（交替色）
        graphics.push({
          type: 'rect', left: box.x, top: box.y, z: -2, silent: true,
          shape: { width: box.width, height: box.height, r: 6 },
          style: { fill: i % 2 === 0 ? 'rgba(0,0,0,0.02)' : 'rgba(0,0,0,0.04)', stroke: 'none' },
        });
        // 阶段标题
        graphics.push({
          type: 'text', left: box.x + box.width / 2, top: 18, z: 0, silent: true,
          style: {
            text: box.label, fontSize: 15, fontWeight: 'bold' as const,
            fill: box.color, textAlign: 'center' as const,
          },
        });
        // 阶段顶部色条
        graphics.push({
          type: 'rect', left: box.x + 10, top: 42, z: 0, silent: true,
          shape: { width: box.width - 20, height: 3, r: 2 },
          style: { fill: box.color },
        });
        // 阶段之间的箭头（除最后一个）
        if (i < stageBoxes.length - 1) {
          const arrowX = box.x + box.width;
          const arrowY = box.height / 2;
          graphics.push({
            type: 'text', left: arrowX - 5, top: arrowY - 8, z: 1, silent: true,
            style: { text: '▸', fontSize: 20, fill: '#ccc' },
          });
        }
      });
    }

    chart.setOption({
      tooltip: { trigger: 'item', confine: true },
      legend: { data: categories.map(c => c.name), orient: 'horizontal', bottom: 10, textStyle: { fontSize: 12 }, itemWidth: 14, itemHeight: 14 },
      graphic: graphics,
      animationDuration: 500,
      series: [{
        type: 'graph', layout: isPipeline ? 'none' : 'force', roam: true, draggable: true, zoom: 1,
        categories, data: nodes, links: edges as any,
        ...(mode === 'force' ? { force: { repulsion: 400, edgeLength: [150, 300], gravity: 0.08, layoutAnimation: true } } : {}),
        emphasis: { focus: 'adjacency', lineStyle: { width: 3 }, itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.3)' } },
        lineStyle: { curveness: 0.2 },
      }],
    }, true);
    chart.resize();
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

  /** 节点下拉选项 */
  const nodeOptions = topoData.current?.nodes.map(n => ({
    value: n.id, label: `${shortName(n.name)}  [${GROUP_CONFIG[n.group]?.label || n.group}]`,
  })) || [];

  /** 当前依赖列表 */
  const currentEdges = topoData.current?.edges || [];

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
            <Radio.Button value="grouped"><ApartmentOutlined /> 管道</Radio.Button>
            <Radio.Button value="force"><NodeIndexOutlined /> 力导向</Radio.Button>
          </Radio.Group>
          <Tooltip title="保存节点位置"><Button icon={<SaveOutlined />} onClick={saveLayout}>保存布局</Button></Tooltip>
          <Tooltip title="重置为自动布局"><Button icon={<UndoOutlined />} onClick={resetLayout}>重置</Button></Tooltip>
          <Button type="primary" icon={<EditOutlined />} onClick={() => setPanelOpen(true)}>编辑依赖</Button>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
        </Space>
      </div>

      {/* 图例 */}
      <div style={{ marginBottom: 8 }}>
        <Space size={16}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            连线: <span style={{ color: '#1890ff' }}>━</span> API 调用　<span style={{ color: '#faad14' }}>╌╌</span> 依赖
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            边框: <span style={{ color: '#52c41a' }}>●</span> 正常　<span style={{ color: '#ff4d4f' }}>●</span> 异常
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>💡 拖拽节点调整位置，点「保存布局」持久化</Text>
        </Space>
      </div>

      {/* 图表 */}
      <Spin spinning={loading}>
        <div ref={chartRef} style={{
          width: '100%', height: 'calc(100vh - 230px)', minHeight: 550,
          background: '#fafafa', borderRadius: 8, border: '1px solid #f0f0f0',
        }} />
      </Spin>

      {/* ===== 编辑面板 (Drawer) ===== */}
      <Drawer
        title="编辑依赖关系"
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        width={500}
      >
        {/* Tab 切换 */}
        <Radio.Group value={aiTab} onChange={e => setAiTab(e.target.value)} style={{ marginBottom: 16, width: '100%' }}
          optionType="button" buttonStyle="solid">
          <Radio.Button value="deps" style={{ width: '50%', textAlign: 'center' }}>
            <UnorderedListOutlined /> 依赖管理
          </Radio.Button>
          <Radio.Button value="ai" style={{ width: '50%', textAlign: 'center' }}>
            <RobotOutlined /> AI 推荐
          </Radio.Button>
        </Radio.Group>

        {aiTab === 'deps' ? (
          <>
            {/* 添加依赖 */}
            <Card size="small" title={<><PlusOutlined /> 添加依赖</>} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>源服务（从）</Text>
                  <Select
                    value={addSource} onChange={setAddSource} placeholder="选择源服务"
                    style={{ width: '100%' }} showSearch optionFilterProp="label"
                    options={nodeOptions}
                  />
                </div>
                <div style={{ textAlign: 'center', color: '#999' }}>↓</div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>目标服务（到）</Text>
                  <Select
                    value={addTarget} onChange={setAddTarget} placeholder="选择目标服务"
                    style={{ width: '100%' }} showSearch optionFilterProp="label"
                    options={nodeOptions}
                  />
                </div>
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>依赖类型</Text>
                  <Select value={addType} onChange={setAddType} style={{ width: '100%' }}
                    options={[
                      { label: '━ API 调用 (calls)', value: 'calls' },
                      { label: '╌ 依赖关系 (depends_on)', value: 'depends_on' },
                    ]}
                  />
                </div>
                <Button type="primary" icon={<PlusOutlined />} onClick={addDependency} block>
                  添加依赖
                </Button>
              </div>
            </Card>

            <Divider />

            {/* 依赖列表 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Text strong>当前依赖 ({currentEdges.length})</Text>
              {currentEdges.some(e => e.manual) && (
                <Popconfirm title="清空所有自定义依赖？" onConfirm={clearAllDeps} okText="清空" okType="danger">
                  <Button size="small" danger icon={<DeleteOutlined />}>清空自定义</Button>
                </Popconfirm>
              )}
            </div>

            {currentEdges.length === 0 ? (
              <Empty description="暂无依赖关系" />
            ) : (
              <List
                size="small"
                dataSource={currentEdges}
                renderItem={(edge) => (
                  <List.Item
                    actions={edge.manual && edge.id ? [
                      <Popconfirm key="del" title="删除此依赖？" onConfirm={() => deleteDependency(edge.id!)} okText="删除" okType="danger">
                        <Button type="link" danger size="small" icon={<DeleteOutlined />} />
                      </Popconfirm>,
                    ] : [<Tag key="auto" style={{ fontSize: 11 }}>自动</Tag>]}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                      <Text ellipsis style={{ maxWidth: 140 }}>{shortName(nodeNameMap.current.get(edge.source) || String(edge.source))}</Text>
                      <span style={{ color: '#999' }}>→</span>
                      <Text ellipsis style={{ maxWidth: 140 }}>{shortName(nodeNameMap.current.get(edge.target) || String(edge.target))}</Text>
                      <Tag color={edge.type === 'calls' ? 'blue' : 'orange'} style={{ marginLeft: 'auto', flexShrink: 0 }}>
                        {edge.type === 'calls' ? '调用' : '依赖'}
                      </Tag>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </>
        ) : (
          /* AI 推荐 Tab */
          <>
            <Button
              type="primary" icon={<RobotOutlined />} onClick={requestAISuggest}
              loading={aiLoading} block style={{ marginBottom: 16 }}
            >
              {aiLoading ? 'AI 分析中...' : '开始 AI 分析'}
            </Button>

            {aiMessage && <Paragraph type="secondary"><BulbOutlined /> {aiMessage}</Paragraph>}

            {aiSuggestions.length > 0 && (
              <Button type="primary" ghost icon={<CheckOutlined />} onClick={applyAllSuggestions} block style={{ marginBottom: 12 }}>
                全部应用 ({aiSuggestions.length} 条)
              </Button>
            )}

            {aiLoading ? (
              <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /><Paragraph style={{ marginTop: 16 }}>AI 正在分析服务关系...</Paragraph></div>
            ) : aiSuggestions.length === 0 ? (
              <Empty description="暂无推荐，点击上方按钮开始分析" />
            ) : (
              <List
                size="small"
                dataSource={aiSuggestions}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button key="apply" type="link" icon={<CheckOutlined />} onClick={() => applyOneSuggestion(item)}>应用</Button>,
                      <Button key="ignore" type="link" danger icon={<CloseOutlined />}
                        onClick={() => setAiSuggestions(prev => prev.filter(x => x !== item))}>忽略</Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space size={4}>
                          <Text strong style={{ fontSize: 13 }}>{shortName(nodeNameMap.current.get(item.source) || '')}</Text>
                          <span style={{ color: '#999' }}>→</span>
                          <Text strong style={{ fontSize: 13 }}>{shortName(nodeNameMap.current.get(item.target) || '')}</Text>
                          <Tag color={item.type === 'calls' ? 'blue' : 'orange'} style={{ fontSize: 11 }}>
                            {item.type === 'calls' ? '调用' : '依赖'}
                          </Tag>
                        </Space>
                      }
                      description={<Text type="secondary" style={{ fontSize: 12 }}>{item.description}</Text>}
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
