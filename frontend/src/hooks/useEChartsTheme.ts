/**
 * ECharts 暗色主题 hook
 * 返回当前主题对应的 ECharts theme 名称和通用样式覆盖
 */
import { useMemo } from 'react';
import { useTheme } from '../contexts/ThemeContext';

/** 暗色模式下的通用文字/轴线颜色 */
const DARK_TEXT = 'rgba(255,255,255,0.85)';
const DARK_AXIS = 'rgba(255,255,255,0.15)';

/**
 * 返回适配当前主题的 ECharts 基础选项覆盖
 * 使用方式：将返回值与业务 option 做 merge
 *
 * ```tsx
 * const { echartsThemeOverrides } = useEChartsTheme();
 * const option = { ...echartsThemeOverrides, ...businessOption };
 * <ReactECharts option={option} theme={isDark ? 'dark' : undefined} />
 * ```
 */
export function useEChartsTheme() {
  const { isDark } = useTheme();

  const echartsTheme = isDark ? 'dark' : undefined;

  const echartsThemeOverrides = useMemo(() => {
    if (!isDark) return {};
    return {
      backgroundColor: 'transparent',
      textStyle: { color: DARK_TEXT },
      title: { textStyle: { color: DARK_TEXT } },
      legend: { textStyle: { color: DARK_TEXT } },
      xAxis: { axisLine: { lineStyle: { color: DARK_AXIS } }, axisLabel: { color: DARK_TEXT }, splitLine: { lineStyle: { color: DARK_AXIS } } },
      yAxis: { axisLine: { lineStyle: { color: DARK_AXIS } }, axisLabel: { color: DARK_TEXT }, splitLine: { lineStyle: { color: DARK_AXIS } } },
    };
  }, [isDark]);

  return { echartsTheme, echartsThemeOverrides, isDark };
}
