/**
 * 日志管理页面
 *
 * 提供两种模式：
 * 1. 搜索模式 - 按关键字、服务器、服务、日志级别、时间范围筛选日志，支持分页
 * 2. 实时模式 - 通过 WebSocket 实时接收并展示日志流，支持暂停/继续和清空
 *
 * 点击日志条目可打开详情抽屉，查看完整消息和前后 5 分钟的上下文日志。
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import {
  Input, Select, DatePicker, Table, Tag, Row, Col, Button, Space, Drawer, Descriptions, Typography, Segmented, Tooltip,
} from 'antd';
import {
  SearchOutlined, PauseCircleOutlined, PlayCircleOutlined, ClearOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { fetchLogs } from '../services/logs';
import type { LogEntry, LogQueryParams } from '../services/logs';
import api from '../services/api';

const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

/** 日志级别对应的 Tag 颜色映射 */
const LEVEL_COLOR: Record<string, string> = {
  DEBUG: 'default',
  INFO: 'blue',
  WARN: 'orange',
  ERROR: 'red',
  FATAL: 'purple',
};

const LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'];

/**
 * 日志管理页面组件
 */
export default function Logs() {
  // ========== 筛选条件状态 ==========
  const [keyword, setKeyword] = useState('');
  const [hostId, setHostId] = useState<string | undefined>();
  const [service, setService] = useState<string | undefined>();
  const [levels, setLevels] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  // ========== 表格数据状态 ==========
  const [data, setData] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  // ========== 服务器/服务下拉选项 ==========
  const [hostOptions, setHostOptions] = useState<{ label: string; value: string }[]>([]);
  const [serviceOptions, setServiceOptions] = useState<{ label: string; value: string }[]>([]);
  /** 主机 ID 到主机名的映射，用于在表格和实时日志中显示主机名 */
  const hostMapRef = useRef<Record<string, string>>({});

  // ========== 模式切换 ==========
  /** 当前模式：search（搜索）或 realtime（实时） */
  const [mode, setMode] = useState<string>('search');

  // ========== 详情抽屉 ==========
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  /** 选中日志前后 5 分钟的上下文日志 */
  const [contextLogs, setContextLogs] = useState<LogEntry[]>([]);
  const [contextLoading, setContextLoading] = useState(false);

  // ========== 实时日志 ==========
  const [realtimeLogs, setRealtimeLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const realtimeEndRef = useRef<HTMLDivElement>(null);
  /** 用 ref 跟踪暂停状态，避免 WebSocket 回调中的闭包问题 */
  const pausedRef = useRef(false);

  // 加载服务器和服务的下拉选项
  useEffect(() => {
    api.get('/hosts', { params: { page_size: 100 } }).then(res => {
      const items = res.data.items || [];
      const opts = items.map((h: { id: number; hostname: string }) => ({ label: h.hostname, value: String(h.id) }));
      setHostOptions(opts);
      // 构建 ID → 主机名 映射表
      const map: Record<string, string> = {};
      items.forEach((h: { id: number; hostname: string }) => { map[String(h.id)] = h.hostname; });
      hostMapRef.current = map;
    }).catch(() => {});
    api.get('/services', { params: { page_size: 100 } }).then(res => {
      const items = res.data.items || [];
      const names = [...new Set(items.map((s: { name: string }) => s.name))] as string[];
      setServiceOptions(names.map(n => ({ label: n, value: n })));
    }).catch(() => {});
  }, []);

  /** 搜索模式日志查询 (Search mode log query)
   * 根据关键字、主机、服务、日志级别、时间范围等条件查询历史日志
   * 支持分页查询，每页默认显示20条记录
   */
  const doFetch = useCallback(async () => {
    setLoading(true);
    try {
      const params: LogQueryParams = { keyword, host_id: hostId, service, level: levels.length ? levels : undefined, page, page_size: pageSize };
      if (timeRange && timeRange[0]) params.start_time = timeRange[0].toISOString();
      if (timeRange && timeRange[1]) params.end_time = timeRange[1].toISOString();
      const res = await fetchLogs(params);
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [keyword, hostId, service, levels, timeRange, page, pageSize]);

  // 搜索模式下，筛选条件变化时自动刷新
  useEffect(() => {
    if (mode === 'search') doFetch();
  }, [mode, doFetch]);

  /** 实时模式 WebSocket 连接管理 (Real-time mode WebSocket connection)
   * 根据筛选条件建立 WebSocket 连接，实时接收日志流
   * 支持按主机、服务、级别、关键字过滤，最多保留500条防止内存溢出
   */
  useEffect(() => {
    if (mode !== 'realtime') {
      wsRef.current?.close();
      wsRef.current = null;
      return;
    }
    // 根据页面协议选择 ws 或 wss
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const params = new URLSearchParams();
    if (hostId) params.set('host_id', hostId);
    if (service) params.set('service', service);
    if (levels.length) params.set('level', levels.join(','));
    if (keyword) params.set('keyword', keyword);
    const url = `${proto}://${window.location.host}/ws/logs?${params.toString()}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setRealtimeLogs([]);

    ws.onmessage = (evt) => {
      // 暂停时不处理新消息，避免界面过载
      if (pausedRef.current) return;
      try {
        const entry: LogEntry = JSON.parse(evt.data);
        setRealtimeLogs(prev => {
          const next = [...prev, entry];
          // 最多保留 500 条，防止内存溢出
          return next.length > 500 ? next.slice(next.length - 500) : next;
        });
      } catch { /* ignore */ }
    };
    ws.onerror = () => {};
    ws.onclose = () => {};

    return () => { ws.close(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, hostId, service, levels, keyword]);

  // 实时模式下自动滚动到最新日志
  useEffect(() => {
    if (mode === 'realtime' && !paused) {
      realtimeEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [realtimeLogs, mode, paused]);

  /** 切换实时日志暂停状态 (Toggle real-time log pause state)
   * 暂停时停止处理 WebSocket 消息，但保持连接
   * 使用 ref 跟踪状态避免 WebSocket 回调中的闭包陷阱
   */
  const togglePause = () => {
    setPaused(p => { pausedRef.current = !p; return !p; });
  };

  /** 打开日志详情和上下文 (Open log details and context)
   * 显示选中日志的完整信息，并加载前后5分钟的相关日志
   * 用于排查问题时了解日志的完整上下文
   */
  const openDrawer = async (log: LogEntry) => {
    setSelectedLog(log);
    setDrawerVisible(true);
    setContextLoading(true);
    try {
      const ts = dayjs(log.timestamp);
      const params: LogQueryParams = {
        start_time: ts.subtract(5, 'minute').toISOString(),
        end_time: ts.add(5, 'minute').toISOString(),
        host_id: log.host_id,
        service: log.service,
        page_size: 21,
      };
      const res = await fetchLogs(params);
      setContextLogs(res.items || []);
    } catch { setContextLogs([]); } finally { setContextLoading(false); }
  };

  /** 日志表格列定义 */
  const columns = [
    { title: '时间', dataIndex: 'timestamp', key: 'timestamp', width: 180, render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm:ss') },
    { title: '服务器', dataIndex: 'hostname', key: 'hostname', width: 140, render: (name: string, record: LogEntry) => name || hostMapRef.current[String(record.host_id)] || `Host #${record.host_id}` },
    { title: '服务', dataIndex: 'service', key: 'service', width: 120 },
    { title: '级别', dataIndex: 'level', key: 'level', width: 90, render: (l: string) => <Tag color={LEVEL_COLOR[l] || 'default'}>{l}</Tag> },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
  ];

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>日志管理</Title>
        {/* 搜索/实时模式切换 */}
        <Segmented options={[{ label: '搜索', value: 'search' }, { label: '实时日志', value: 'realtime' }]} value={mode} onChange={v => setMode(v as string)} />
      </Row>

      {/* 筛选条件栏 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Input.Search placeholder="关键字搜索" allowClear prefix={<SearchOutlined />} value={keyword} onChange={e => setKeyword(e.target.value)} onSearch={() => { if (mode === 'search') { setPage(1); doFetch(); } }} />
        </Col>
        <Col xs={12} sm={6} md={4}>
          <Select placeholder="服务器" allowClear style={{ width: '100%' }} options={hostOptions} value={hostId} onChange={setHostId} showSearch optionFilterProp="label" />
        </Col>
        <Col xs={12} sm={6} md={4}>
          <Select placeholder="服务" allowClear style={{ width: '100%' }} options={serviceOptions} value={service} onChange={setService} showSearch optionFilterProp="label" />
        </Col>
        <Col xs={24} sm={12} md={5}>
          <Select mode="multiple" placeholder="日志级别" allowClear style={{ width: '100%' }} options={LEVELS.map(l => ({ label: l, value: l }))} value={levels} onChange={setLevels} />
        </Col>
        {mode === 'search' && (
          <Col xs={24} sm={12} md={5}>
            <RangePicker showTime style={{ width: '100%' }} value={timeRange as [Dayjs, Dayjs] | null} onChange={(v) => setTimeRange(v)} />
          </Col>
        )}
      </Row>

      {/* 搜索模式：分页表格 */}
      {mode === 'search' && (
        <Table
          dataSource={data}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ current: page, pageSize, total, showSizeChanger: true, showTotal: t => `共 ${t} 条`, onChange: (p, ps) => { setPage(p); setPageSize(ps); } }}
          onRow={(record) => ({ onClick: () => openDrawer(record), style: { cursor: 'pointer' } })}
        />
      )}

      {/* 实时模式：终端风格日志流 */}
      {mode === 'realtime' && (
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Tooltip title={paused ? '继续' : '暂停'}>
              <Button icon={paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />} onClick={togglePause}>
                {paused ? '继续' : '暂停'}
              </Button>
            </Tooltip>
            <Button icon={<ClearOutlined />} onClick={() => setRealtimeLogs([])}>清空</Button>
            <Text type="secondary">{realtimeLogs.length} 条</Text>
          </Space>
          {/* 终端样式日志展示区 */}
          <div style={{
            background: '#1e1e1e', color: '#d4d4d4', fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            fontSize: 13, lineHeight: 1.6, padding: 16, borderRadius: 8, height: 500, overflowY: 'auto',
          }}>
            {realtimeLogs.map((log, i) => (
              <div key={`${log.id || i}`} style={{ cursor: 'pointer' }} onClick={() => openDrawer(log)}>
                <span style={{ color: '#888' }}>{dayjs(log.timestamp).format('HH:mm:ss.SSS')}</span>
                {' '}
                <span style={{ color: { DEBUG: '#888', INFO: '#4fc1ff', WARN: '#cca700', ERROR: '#f44747', FATAL: '#c586c0' }[log.level] || '#d4d4d4' }}>
                  [{log.level}]
                </span>
                {' '}
                <span style={{ color: '#9cdcfe' }}>{hostMapRef.current[String(log.host_id)] || `Host#${log.host_id}`}/{log.service}</span>
                {' '}
                <span>{log.message}</span>
              </div>
            ))}
            <div ref={realtimeEndRef} />
          </div>
        </div>
      )}

      {/* 日志详情抽屉 */}
      <Drawer
        title="日志详情"
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={640}
      >
        {selectedLog && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="时间">{dayjs(selectedLog.timestamp).format('YYYY-MM-DD HH:mm:ss.SSS')}</Descriptions.Item>
              <Descriptions.Item label="服务器">{selectedLog.hostname}</Descriptions.Item>
              <Descriptions.Item label="服务">{selectedLog.service}</Descriptions.Item>
              <Descriptions.Item label="级别"><Tag color={LEVEL_COLOR[selectedLog.level]}>{selectedLog.level}</Tag></Descriptions.Item>
              {selectedLog.file_path && <Descriptions.Item label="文件路径">{selectedLog.file_path}</Descriptions.Item>}
            </Descriptions>

            <Title level={5}>消息内容</Title>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 200, overflow: 'auto' }}>
              {selectedLog.message}
            </pre>

            {/* 上下文日志：选中日志前后 5 分钟内的相关日志 */}
            <Title level={5} style={{ marginTop: 16 }}>上下文日志</Title>
            <Table
              dataSource={contextLogs}
              columns={columns}
              rowKey={(r, i) => r.id || String(i)}
              loading={contextLoading}
              size="small"
              pagination={false}
              rowClassName={(record) => record.id === selectedLog.id ? 'ant-table-row-selected' : ''}
            />
          </>
        )}
      </Drawer>
    </div>
  );
}
