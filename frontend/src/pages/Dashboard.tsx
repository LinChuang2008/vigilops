/**
 * 仪表盘页面 - 可定制化版本
 * 
 * 功能特性：
 * - 支持拖拽调整组件位置和大小
 * - 可控制各组件的显示/隐藏
 * - 布局配置可导出/导入
 * - 支持实时 WebSocket 数据推送
 * - 响应式设计适配各种屏幕
 */

import CustomizableDashboard from '../components/dashboard/CustomizableDashboard';

export default function Dashboard() {
  return <CustomizableDashboard />;
}