/**
 * 公共状态颜色映射
 * 统一 Dashboard/AlertList/ServiceList 中的颜色定义
 */
import i18n from '../i18n';

/** 告警严重级别颜色 */
export const severityColor: Record<string, string> = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};

/** 告警状态颜色 */
export const alertStatusColor: Record<string, string> = {
  firing: 'red',
  resolved: 'green',
  acknowledged: 'blue',
};

/** 服务状态颜色 */
export function serviceStatusColor(s: string): string {
  if (s === 'healthy' || s === 'up') return 'success';
  if (s === 'degraded') return 'warning';
  return 'error';
}

/** 服务状态文本 */
export function serviceStatusText(s: string): string {
  if (s === 'healthy' || s === 'up') return i18n.t('services.healthy');
  if (s === 'degraded') return i18n.t('services.degraded');
  return i18n.t('common.unhealthy');
}
