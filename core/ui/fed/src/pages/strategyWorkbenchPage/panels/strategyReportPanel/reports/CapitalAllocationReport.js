import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import { buildCapitalSampleStockRows } from '../../../mocks/strategyReportSampleRows';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import { formatReportChartDateLabel } from '../lib/reportDateFormat';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_SPLIT_LINE,
} from '../lib/reportChartsTheme';

/** 资产曲线纵轴按数据区间缩放（不再默认贴 0），少量留白便于读出波动 */
function equityAxisMinMax(equityCurveValues) {
  const nums = (equityCurveValues || [])
    .map((v) => Number(v))
    .filter((v) => Number.isFinite(v));
  if (nums.length === 0) return {};
  const minV = Math.min(...nums);
  const maxV = Math.max(...nums);
  const span = Math.max(maxV - minV, Math.abs(minV) * 0.02, Math.abs(maxV) * 0.02, 1);
  const pad = span * 0.12;
  return {
    min: minV - pad,
    max: maxV + pad,
  };
}

function buildEquityCurveOption(metrics) {
  const { min: yMin, max: yMax } = equityAxisMinMax(metrics.equityCurveValues);
  return {
    animation: false,
    grid: REPORT_CHART_GRID_BASE,
    xAxis: {
      type: 'category',
      data: metrics.equityCurveLabels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (v) => formatReportChartDateLabel(v),
      },
    },
    yAxis: {
      type: 'value',
      ...((yMin !== undefined && yMax !== undefined) ? { min: yMin, max: yMax } : {}),
      splitNumber: 4,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (value) => `${(value / 10000).toFixed(0)}w`,
      },
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'line',
        data: metrics.equityCurveValues,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#4CAF50' },
        areaStyle: { color: 'rgba(76, 175, 80, 0.16)' },
      },
    ],
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${formatReportChartDateLabel(point.axisValue)}<br/>总资产：${Number(point.data).toLocaleString()}`;
      },
    },
  };
}

function buildDrawdownCurveOption(metrics) {
  return {
    animation: false,
    grid: REPORT_CHART_GRID_BASE,
    xAxis: {
      type: 'category',
      data: metrics.equityCurveLabels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (v) => formatReportChartDateLabel(v),
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...REPORT_CHART_AXIS_LABEL, formatter: '{value}%' },
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'line',
        data: metrics.drawdownCurveValues,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#EF5350' },
        areaStyle: { color: 'rgba(239, 83, 80, 0.14)' },
      },
    ],
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${formatReportChartDateLabel(point.axisValue)}<br/>回撤：${point.data}%`;
      },
    },
  };
}

function CapitalAllocationReport({ metrics, stockRows, title = '资金模拟报告（草图）', showStockGrid = true }) {
  const [stockSearch, setStockSearch] = useState('');

  const derivedStockRows = useMemo(() => {
    if (Array.isArray(stockRows) && stockRows.length > 0) return stockRows;
    return buildCapitalSampleStockRows(metrics || {});
  }, [metrics, stockRows]);

  const filteredRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    const filtered = keyword
      ? derivedStockRows.filter((row) => (
        row.stockCode.toLowerCase().includes(keyword) || row.stockName.toLowerCase().includes(keyword)
      ))
      : derivedStockRows;
    return filtered;
  }, [derivedStockRows, stockSearch]);

  const stockColumns = [
    { field: 'stockCode', headerName: '代码', flex: 1, minWidth: 120 },
    { field: 'stockName', headerName: '名称', flex: 1, minWidth: 120 },
    {
      field: 'tradeCount',
      headerName: '交易次数',
      width: 110,
      valueFormatter: (params) => `${params.value} 次`,
    },
    {
      field: 'pnl',
      headerName: '累计盈亏',
      width: 130,
      valueFormatter: (params) => `${params.value >= 0 ? '+' : ''}${Number(params.value).toLocaleString()}`,
    },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
  ];

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      {showStockGrid ? (
        <ReportStockSampleGrid
          title="逐股样本"
          tip="用于查看资金模拟阶段的单股交易结果；支持搜索、表头排序与底部分页。"
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          rows={filteredRows}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="资金结果总览"
        tip="先看赚了多少、承受了多大回撤，并结合资产曲线判断收益路径是否平滑。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="初始资金" value={metrics.initialCapital.toLocaleString()} />
          <MetricCard title="最终总资产" value={metrics.finalEquity.toLocaleString()} />
          <MetricCard title="总收益率" value={`${metrics.totalReturnPct}%`} />
          <MetricCard title="收益回撤比（Calmar）" value={metrics.calmarRatio} />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            资产曲线（总资产随时间变化）
          </Typography>
          <ReactECharts
            option={buildEquityCurveOption(metrics)}
            style={{ height: 180, width: '100%' }}
            notMerge
            lazyUpdate
          />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="交易质量"
        tip="用于判断收益是否来自稳定交易，而不是少数极端收益单。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="总交易次数" value={metrics.totalTrades.toLocaleString()} hint={`买入 ${metrics.buyTrades} / 卖出 ${metrics.sellTrades}`} />
          <MetricCard title="胜率" value={`${metrics.winRatePct}%`} hint={`盈利 ${metrics.winTrades} / 亏损 ${metrics.lossTrades}`} />
          <MetricCard title="总盈亏金额" value={metrics.totalProfit.toLocaleString()} />
          <MetricCard title="单笔平均盈亏" value={metrics.avgPnlPerTrade.toLocaleString()} />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="仓位与资金利用率"
        tip="用于观察资金是否有效投入市场，以及是否长期处于空仓或满仓。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="平均持仓数" value={`${metrics.avgOpenPositions} / ${metrics.peakPositions}`} />
          <MetricCard title="满仓天数占比" value={`${metrics.fullExposureDaysRatio}%`} />
          <MetricCard title="平均现金占比" value={`${metrics.avgCashRatio}%`} />
          <MetricCard title="资金利用率" value={`${metrics.capitalUtilizationRatio}%`} />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="风险结构"
        tip="用于识别最坏情境：连续亏损、回撤持续和尾部亏损规模。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="最大回撤" value={`${metrics.maxDrawdownPct}%`} />
          <MetricCard title="最大回撤持续天数" value={`${metrics.maxDrawdownDurationDays} 天`} />
          <MetricCard title="最长连续亏损" value={`${metrics.maxLossStreak} 笔`} />
          <MetricCard
            title="Top3 单笔亏损"
            value={metrics.worstTradePnls.map((value) => value.toLocaleString()).join(' / ')}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            回撤曲线（资产曲线对应的回撤深度）
          </Typography>
          <ReactECharts
            option={buildDrawdownCurveOption(metrics)}
            style={{ height: 170, width: '100%' }}
            notMerge
            lazyUpdate
          />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="股票集中度"
        tip="用于评估收益是否过度依赖少数股票，降低回测结果偶然性。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="触发股票数" value={metrics.stockCount.toLocaleString()} />
          <MetricCard title="每股平均交易次数" value={metrics.avgTradesPerStock.toFixed(2)} />
          <MetricCard title="前 5 股票收益贡献占比" value={`${metrics.top5ContributionRatio}%`} />
          <MetricCard title="股票收益离散系数（CV）" value={metrics.stockPnlCv} />
        </Box>
      </SectionBlock>
    </Stack>
  );
}

export default CapitalAllocationReport;
