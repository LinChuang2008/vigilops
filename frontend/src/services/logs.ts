/**
 * 日志服务模块
 * 提供日志查询和日志统计的 API 调用
 */
import api from './api';

/** 单条日志记录 */
export interface LogEntry {
  id: string;
  /** 日志时间戳 */
  timestamp: string;
  /** 来源主机 ID */
  host_id: string;
  /** 来源主机名 */
  hostname: string;
  /** 服务名称 */
  service: string;
  /** 日志级别 */
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
  /** 日志内容 */
  message: string;
  /** 日志文件路径 */
  file_path?: string;
  /** 日志来源标识 */
  source?: string;
}

/** 日志列表响应 */
export interface LogsResponse {
  items: LogEntry[];
  total: number;
}

/** 按级别统计数量 */
export interface LevelCount {
  level: string;
  count: number;
}

/** 按时间段统计数量 */
export interface TimeCount {
  /** 时间桶（聚合时间点） */
  time_bucket: string;
  count: number;
}

/** 日志统计数据 */
export interface LogStats {
  /** 按日志级别分布 */
  by_level: LevelCount[];
  /** 按时间趋势分布 */
  by_time: TimeCount[];
}

/** 日志查询参数 */
export interface LogQueryParams {
  /** 关键词搜索 */
  keyword?: string;
  /** 按主机过滤 */
  host_id?: string;
  /** 按服务过滤 */
  service?: string;
  /** 按日志级别过滤（多选） */
  level?: string[];
  /** 开始时间 */
  start_time?: string;
  /** 结束时间 */
  end_time?: string;
  page?: number;
  page_size?: number;
}

/**
 * 查询日志列表
 * @param params 查询参数
 */
export async function fetchLogs(params: LogQueryParams): Promise<LogsResponse> {
  const query: Record<string, unknown> = { ...params };
  // 将 level 数组转为逗号分隔字符串，适配后端接口格式
  if (params.level && params.level.length > 0) {
    query.level = params.level.join(',');
  }
  const res = await api.get('/logs', { params: query });
  return res.data;
}

/**
 * 获取日志统计数据
 * @param period 统计时间范围（默认 1h）
 */
export async function fetchLogStats(period: string = '1h'): Promise<LogStats> {
  const res = await api.get('/logs/stats', { params: { period } });
  return res.data;
}
