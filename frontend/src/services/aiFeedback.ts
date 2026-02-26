/**
 * AI 反馈服务
 */
import api from './api';

export interface AIFeedback {
  id: number;
  session_id?: string;
  message_id?: string;
  ai_response: string;
  user_question?: string;
  rating: number;
  feedback_type: string;
  feedback_text?: string;
  is_helpful?: boolean;
  context?: Record<string, any>;
  ai_confidence?: number;
  response_time_ms?: number;
  is_reviewed: boolean;
  reviewer_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface FeedbackStats {
  total_feedback: number;
  avg_rating?: number;
  helpful_percentage?: number;
  rating_distribution: Record<string, number>;
  feedback_by_type: Record<string, number>;
  avg_response_time_ms?: number;
  avg_confidence?: number;
  trends: Record<string, any>;
}

export interface QuickFeedbackData {
  session_id?: string;
  message_id?: string;
  ai_response: string;
  rating: number;
  is_helpful?: boolean;
}

export interface FeedbackCreateData {
  session_id?: string;
  message_id?: string;
  ai_response: string;
  user_question?: string;
  rating: number;
  feedback_type?: string;
  feedback_text?: string;
  is_helpful?: boolean;
  context?: Record<string, any>;
  ai_confidence?: number;
  response_time_ms?: number;
}

export interface FeedbackTrend {
  date: string;
  avg_rating?: number;
  feedback_count: number;
  helpful_count: number;
}

export const aiFeedbackService = {
  /** 创建反馈 */
  createFeedback: (data: FeedbackCreateData) =>
    api.post<AIFeedback>('/ai-feedback', data),

  /** 快速反馈（只需评分） */
  quickFeedback: (data: QuickFeedbackData) =>
    api.post<AIFeedback>('/ai-feedback/quick', data),

  /** 获取反馈列表 */
  listFeedback: (params?: {
    page?: number;
    page_size?: number;
    rating?: number;
    feedback_type?: string;
    is_helpful?: boolean;
    is_reviewed?: boolean;
    start_date?: string;
    end_date?: string;
  }) => api.get<{ total: number; items: AIFeedback[] }>('/ai-feedback', { params }),

  /** 获取反馈统计 */
  getStats: (days?: number) =>
    api.get<FeedbackStats>('/ai-feedback/stats', { params: { days } }),

  /** 获取反馈趋势 */
  getTrends: (days?: number) =>
    api.get<FeedbackTrend[]>('/ai-feedback/trends', { params: { days } }),

  /** 更新反馈 */
  updateFeedback: (id: number, data: Partial<FeedbackCreateData>) =>
    api.put<AIFeedback>(`/ai-feedback/${id}`, data),

  /** 删除反馈 */
  deleteFeedback: (id: number) => api.delete(`/ai-feedback/${id}`),

  /** 获取性能报告（管理员）*/
  getPerformanceReport: (period?: '7d' | '30d' | '90d') =>
    api.get('/ai-feedback/report', { params: { period } }),
};