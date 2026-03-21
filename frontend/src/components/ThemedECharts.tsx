/**
 * 主题感知的 ECharts 包装组件
 * 自动应用暗色/亮色主题，透明背景
 */

import ReactECharts, { type EChartsOption } from 'echarts-for-react';
import { useTheme } from '../contexts/ThemeContext';
import { useMemo, type CSSProperties, forwardRef } from 'react';
import { theme } from 'antd';

const { useToken } = theme;

interface ThemedEChartsProps {
  option: EChartsOption;
  style?: CSSProperties;
  opts?: any;
  notMerge?: boolean;
  lazyUpdate?: boolean;
  onEvents?: Record<string, Function>;
  onChartReady?: (instance: any) => void;
}

const ThemedECharts = forwardRef<any, ThemedEChartsProps>(({ option, ...rest }, ref) => {
  const { isDark } = useTheme();
  const { token } = useToken(); // Get Ant Design theme tokens

  const themedOption = useMemo(() => {
    if (!isDark) return option;

    // Use Ant Design tokens instead of hardcoded RGBA strings
    const textColor = token.colorTextSecondary;
    const splitColor = token.colorBorderSecondary; 

    // Deep merge dark overrides into option
    const darkOption = { ...option, backgroundColor: 'transparent' };

    // Title + subtitle
    if (darkOption.title) {
      const t = Array.isArray(darkOption.title) ? darkOption.title : [darkOption.title];
      darkOption.title = t.map((item: any) => ({
        ...item,
        textStyle: { color: textColor, ...item?.textStyle },
        subtextStyle: { color: textColor, ...item?.subtextStyle },
      }));
      if (!Array.isArray(option.title)) darkOption.title = darkOption.title[0];
    }

    // Legend
    if (darkOption.legend) {
      darkOption.legend = { ...darkOption.legend, textStyle: { color: textColor, ...(darkOption.legend as any)?.textStyle } };
    }

    // Axes
    const patchAxis = (axis: any) => {
      if (!axis) return axis;
      const arr = Array.isArray(axis) ? axis : [axis];
      const patched = arr.map((a: any) => ({
        ...a,
        axisLabel: { color: textColor, ...a?.axisLabel },
        axisLine: { lineStyle: { color: splitColor, ...a?.axisLine?.lineStyle }, ...a?.axisLine },
        splitLine: { lineStyle: { color: splitColor, ...a?.splitLine?.lineStyle }, ...a?.splitLine },
      }));
      return Array.isArray(axis) ? patched : patched[0];
    };
    if (darkOption.xAxis) darkOption.xAxis = patchAxis(darkOption.xAxis);
    if (darkOption.yAxis) darkOption.yAxis = patchAxis(darkOption.yAxis);

    return darkOption;
  }, [option, isDark, token.colorTextSecondary, token.colorBorderSecondary]); // Added tokens to dependencies

  return (
    <ReactECharts
      ref={ref as any}
      option={themedOption}
      theme={isDark ? 'dark' : undefined}
      {...rest}
    />
  );
});

ThemedECharts.displayName = 'ThemedECharts';
export default ThemedECharts;