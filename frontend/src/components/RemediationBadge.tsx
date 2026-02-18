/**
 * 修复状态标签组件
 * 根据修复任务状态和风险级别渲染对应颜色的 Tag
 */
import { Tag } from 'antd';

/** 状态 → 颜色映射 */
const statusConfig: Record<string, { color: string; label: string }> = {
  pending:   { color: 'orange',  label: '待审批' },
  approved:  { color: 'blue',    label: '已审批' },
  executing: { color: 'processing', label: '执行中' },
  success:   { color: 'success', label: '已完成' },
  failed:    { color: 'error',   label: '失败' },
  rejected:  { color: 'default', label: '已拒绝' },
};

/** 风险级别 → 颜色映射 */
const riskConfig: Record<string, { color: string; label: string }> = {
  low:      { color: 'green',  label: '低' },
  medium:   { color: 'orange', label: '中' },
  high:     { color: 'red',    label: '高' },
  critical: { color: '#cf1322', label: '严重' },
};

/** 修复状态标签 */
export function RemediationStatusTag({ status }: { status: string }) {
  const cfg = statusConfig[status] || { color: 'default', label: status };
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
}

/** 风险级别标签 */
export function RiskLevelTag({ level }: { level: string }) {
  const cfg = riskConfig[level] || { color: 'default', label: level };
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
}
