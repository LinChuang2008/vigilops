/**
 * 运维报告 API 服务
 * 提供报告的增删查及生成功能
 */
import api from './api';

/** 运维报告数据结构 */
export interface Report {
  id: number;
  title: string;
  report_type: string;
  period_start: string;
  period_end: string;
  content: string;
  summary: string;
  status: string;
  generated_by: number | null;
  created_at: string;
}

/** 生成报告请求参数 */
export interface GenerateReportRequest {
  report_type: string;
  period_start?: string;
  period_end?: string;
}

/** 分页报告列表响应 */
export interface ReportListResponse {
  items: Report[];
  total: number;
}

/** 获取报告列表 */
export const fetchReports = (page = 1, pageSize = 10) =>
  api.get<ReportListResponse>('/reports', { params: { page, page_size: pageSize } });

/** 获取报告详情 */
export const fetchReport = (id: number) =>
  api.get<Report>(`/reports/${id}`);

/** 生成报告 */
export const generateReport = (data: GenerateReportRequest) =>
  api.post<Report>('/reports/generate', data);

/** 删除报告 */
export const deleteReport = (id: number) =>
  api.delete(`/reports/${id}`);
