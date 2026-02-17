/**
 * 通知模板 API 服务
 * 提供通知模板的增删改查接口
 */
import api from './api';

/** 通知模板数据结构 */
export interface NotificationTemplate {
  id: number;
  /** 模板名称 */
  name: string;
  /** 适用渠道类型（webhook/email/dingtalk/feishu/wecom/all） */
  channel_type: string;
  /** 标题模板（仅邮件类型使用） */
  subject_template: string | null;
  /** 消息体模板 */
  body_template: string;
  /** 是否为默认模板 */
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

/** 通知模板创建/更新参数 */
export interface NotificationTemplatePayload {
  name: string;
  channel_type: string;
  subject_template?: string | null;
  body_template: string;
  is_default?: boolean;
}

/** 通知模板服务 */
export const notificationTemplateService = {
  /** 获取所有通知模板 */
  fetchTemplates: () => api.get<NotificationTemplate[]>('/notification-templates'),
  /** 创建通知模板 */
  createTemplate: (data: NotificationTemplatePayload) => api.post<NotificationTemplate>('/notification-templates', data),
  /** 更新通知模板 */
  updateTemplate: (id: number, data: Partial<NotificationTemplatePayload>) => api.put<NotificationTemplate>(`/notification-templates/${id}`, data),
  /** 删除通知模板 */
  deleteTemplate: (id: number) => api.delete(`/notification-templates/${id}`),
};
