/**
 * 自定义 Runbook 服务模块
 * 提供自定义 Runbook 的 CRUD 和 Dry-run API 调用
 */
import api from './api';

/** Runbook 步骤 */
export interface RunbookStep {
  name: string;
  command: string;
  timeout_sec: number;
  rollback_command?: string | null;
}

/** 自定义 Runbook */
export interface CustomRunbook {
  id: number;
  name: string;
  description: string;
  trigger_keywords: string[];
  risk_level: string;
  steps: RunbookStep[];
  safety_checks: string[];
  created_by: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Runbook 列表项 */
export interface RunbookListItem {
  id: number;
  name: string;
  description: string;
  source: 'custom';
  risk_level: string;
  trigger_keywords?: string[];
  steps_count: number;
  is_active: boolean;
  created_at?: string;
}

/** Dry-run 步骤结果 */
export interface DryRunStepResult {
  step_name: string;
  resolved_command: string;
  timeout_sec: number;
  rollback_command?: string | null;
  safety_check_passed: boolean;
  safety_message: string;
}

/** Dry-run 响应 */
export interface DryRunResponse {
  runbook_name: string;
  risk_level: string;
  total_steps: number;
  steps: DryRunStepResult[];
  all_safe: boolean;
}

/** 创建请求 */
export interface CreateRunbookRequest {
  name: string;
  description?: string;
  trigger_keywords?: string[];
  risk_level?: string;
  steps: RunbookStep[];
  safety_checks?: string[];
  is_active?: boolean;
}

/** 更新请求 */
export type UpdateRunbookRequest = Partial<CreateRunbookRequest>;

/** AI 生成 Runbook 请求 */
export interface GenerateRunbookRequest {
  description: string;
  risk_level?: string;
}

/** AI 生成 Runbook 响应 */
export interface GenerateRunbookResponse {
  success: boolean;
  runbook?: CreateRunbookRequest & { name: string; description: string };
  error?: string;
  safety_warnings: string[];
}

export const customRunbookService = {
  /** 获取所有 Runbook */
  listAll: () =>
    api.get<{ items: RunbookListItem[]; total: number }>('/runbooks/custom/all'),

  /** 获取自定义 Runbook 列表 */
  list: (params?: Record<string, unknown>) =>
    api.get<CustomRunbook[]>('/runbooks/custom', { params }),

  /** 获取单个自定义 Runbook */
  get: (id: number) => api.get<CustomRunbook>(`/runbooks/custom/${id}`),

  /** 创建自定义 Runbook */
  create: (data: CreateRunbookRequest) =>
    api.post<CustomRunbook>('/runbooks/custom', data),

  /** 更新自定义 Runbook */
  update: (id: number, data: UpdateRunbookRequest) =>
    api.put<CustomRunbook>(`/runbooks/custom/${id}`, data),

  /** 删除自定义 Runbook */
  delete: (id: number) => api.delete(`/runbooks/custom/${id}`),

  /** Dry-run */
  dryRun: (id: number, variables?: Record<string, string>) =>
    api.post<DryRunResponse>(`/runbooks/custom/${id}/dry-run`, { variables: variables || {} }),

  /** 导出 */
  exportAll: () =>
    api.get('/runbooks/custom/export/all', { responseType: 'blob' }),

  /** AI 生成 Runbook */
  generateWithAI: (data: GenerateRunbookRequest) =>
    api.post<GenerateRunbookResponse>('/ai/generate-runbook', data, { timeout: 60000 }),

  /** 导入 */
  importFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/runbooks/custom/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
