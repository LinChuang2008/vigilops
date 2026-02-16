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

const LEVEL_COLOR: Record<string, string> = {
  DEBUG: 'default',
  INFO: 'blue',
  WARN: 'orange',
  ERROR: 'red',
  FATAL: 'purple',
};

const LEVELS = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL'];

export default function Logs() {
  // --- filter state ---
  const [keyword, setKeyword] = useState('');
  const [hostId, setHostId] = useState<string | undefined>();
  const [service, setService] = useState<string | undefined>();
  const [levels, setLevels] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  // --- table state ---
  const [data, setData] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  // --- hosts / services options ---
  const [hostOptions, setHostOptions] = useState<{ label: string; value: string }[]>([]);
  const [serviceOptions, setServiceOptions] = useState<{ label: string; value: string }[]>([]);
  const hostMapRef = useRef<Record<string, string>>({});

  // --- mode ---
  const [mode, setMode] = useState<string>('search');

  // --- drawer ---
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [contextLogs, setContextLogs] = useState<LogEntry[]>([]);
  const [contextLoading, setContextLoading] = useState(false);

  // --- realtime ---
  const [realtimeLogs, setRealtimeLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const realtimeEndRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(false);

  // load host/service options
  useEffect(() => {
    api.get('/hosts', { params: { page_size: 200 } }).then(res => {
      const items = res.data.items || [];
      const opts = items.map((h: { id: number; hostname: string }) => ({ label: h.hostname, value: String(h.id) }));
      setHostOptions(opts);
      const map: Record<string, string> = {};
      items.forEach((h: { id: number; hostname: string }) => { map[String(h.id)] = h.hostname; });
      hostMapRef.current = map;
    }).catch(() => {});
    api.get('/services', { params: { page_size: 200 } }).then(res => {
      const items = res.data.items || [];
      const names = [...new Set(items.map((s: { name: string }) => s.name))] as string[];
      setServiceOptions(names.map(n => ({ label: n, value: n })));
    }).catch(() => {});
  }, []);

  // --- fetch logs ---
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

  useEffect(() => {
    if (mode === 'search') doFetch();
  }, [mode, doFetch]);

  // --- websocket realtime ---
  useEffect(() => {
    if (mode !== 'realtime') {
      wsRef.current?.close();
      wsRef.current = null;
      return;
    }
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
      if (pausedRef.current) return;
      try {
        const entry: LogEntry = JSON.parse(evt.data);
        setRealtimeLogs(prev => {
          const next = [...prev, entry];
          return next.length > 500 ? next.slice(next.length - 500) : next;
        });
      } catch { /* ignore */ }
    };
    ws.onerror = () => {};
    ws.onclose = () => {};

    return () => { ws.close(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, hostId, service, levels, keyword]);

  // auto scroll
  useEffect(() => {
    if (mode === 'realtime' && !paused) {
      realtimeEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [realtimeLogs, mode, paused]);

  const togglePause = () => {
    setPaused(p => { pausedRef.current = !p; return !p; });
  };

  // --- drawer context ---
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

  // --- columns ---
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
        <Segmented options={[{ label: '搜索', value: 'search' }, { label: '实时日志', value: 'realtime' }]} value={mode} onChange={v => setMode(v as string)} />
      </Row>

      {/* Filters */}
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

      {/* Search mode */}
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

      {/* Realtime mode */}
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

      {/* Drawer - F056 */}
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
