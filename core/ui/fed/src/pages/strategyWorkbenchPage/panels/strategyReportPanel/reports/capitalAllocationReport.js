import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import {
  CAPITAL_CHART_TIPS,
  CAPITAL_METRIC_TIPS,
  CAPITAL_SECTION_TIPS,
  REPORT_STOCK_GRID_TIPS,
} from '../reportMetricTips';
import { formatReportMoney } from '../lib/formatReportMoney';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import { formatReportChartDateLabel } from '../lib/reportDateFormat';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
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
      ...REPORT_CHART_TOOLTIP,
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
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${formatReportChartDateLabel(point.axisValue)}<br/>回撤：${point.data}%`;
      },
    },
  };
}

function CapitalAllocationReport({
  metrics,
  stockRows,
  title = '资金模拟报告',
  showStockGrid = true,
  hideTitle = false,
}) {
  const [stockSearch, setStockSearch] = useState('');

  const derivedStockRows = useMemo(() => (
    Array.isArray(stockRows) && stockRows.length > 0 ? stockRows : []
  ), [stockRows]);

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
      valueFormatter: (params) => `${params.value >= 0 ? '+' : ''}${formatReportMoney(params.value)}`,
    },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
  ];

  if (!metrics || typeof metrics !== 'object') {
    return <ReportUnavailableHint />;
  }

  const executionSkipsAvail = metrics?._availability?.executionSkips ?? false;

  const showStockSampleGrid = Boolean(showStockGrid && derivedStockRows.length > 0);

  return (
    <Stack spacing={1.25}>
      {!hideTitle ? (
        <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>
      ) : null}

      {showStockSampleGrid ? (
        <ReportStockSampleGrid
          title="逐股样本"
          tip={REPORT_STOCK_GRID_TIPS.capital}
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          rows={filteredRows}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="资金结果总览"
        tip={CAPITAL_SECTION_TIPS.overview}
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="初始资金"
            titleTip={CAPITAL_METRIC_TIPS.initialCapital}
            value={formatReportMoney(metrics.initialCapital)}
          />
          <MetricCard
            title="最终总资产"
            titleTip={CAPITAL_METRIC_TIPS.finalEquity}
            value={formatReportMoney(metrics.finalEquity)}
          />
          <MetricCard
            title="总收益率"
            titleTip={CAPITAL_METRIC_TIPS.totalReturnPct}
            value={`${metrics.totalReturnPct}%`}
          />
          <MetricCard
            title="收益回撤比（Calmar）"
            titleTip={CAPITAL_METRIC_TIPS.calmarRatio}
            value={metrics.calmarRatio}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              资产曲线
            </Typography>
            <NtqHelpTooltip title={CAPITAL_CHART_TIPS.equityCurve} />
          </Stack>
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
        tip={CAPITAL_SECTION_TIPS.tradeQuality}
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="总交易次数"
            titleTip={CAPITAL_METRIC_TIPS.totalTrades}
            value={metrics.totalTrades.toLocaleString()}
            hint={`买入 ${metrics.buyTrades} / 卖出 ${metrics.sellTrades}`}
          />
          <MetricCard
            title="胜率"
            titleTip={CAPITAL_METRIC_TIPS.winRate}
            value={`${metrics.winRatePct}%`}
            hint={`盈利 ${metrics.winTrades} / 亏损 ${metrics.lossTrades}`}
          />
          <MetricCard
            title="总盈亏金额"
            titleTip={CAPITAL_METRIC_TIPS.totalProfit}
            value={formatReportMoney(metrics.totalProfit)}
          />
          <MetricCard
            title="单笔平均盈亏"
            titleTip={CAPITAL_METRIC_TIPS.avgPnlPerTrade}
            value={formatReportMoney(metrics.avgPnlPerTrade)}
          />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="成交跳过统计"
        tip={CAPITAL_SECTION_TIPS.executionSkips}
      >
        {executionSkipsAvail ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="涨停跳过买入"
              titleTip={CAPITAL_METRIC_TIPS.skippedBuyAtLimitUp}
              value={metrics.skippedBuyAtLimitUp.toLocaleString()}
            />
            <MetricCard
              title="跌停跳过卖出"
              titleTip={CAPITAL_METRIC_TIPS.skippedSellAtLimitDown}
              value={metrics.skippedSellAtLimitDown.toLocaleString()}
            />
            <MetricCard
              title="状态跳过投资"
              titleTip={CAPITAL_METRIC_TIPS.skippedStockStatus}
              value={metrics.skippedStockStatus.toLocaleString()}
            />
            <MetricCard
              title="参与率跳过买入"
              titleTip={CAPITAL_METRIC_TIPS.skippedBuyParticipation}
              value={metrics.skippedBuyParticipation.toLocaleString()}
            />
            <MetricCard
              title="参与率跳过卖出"
              titleTip={CAPITAL_METRIC_TIPS.skippedSellParticipation}
              value={metrics.skippedSellParticipation.toLocaleString()}
            />
            <MetricCard
              title="参与率缩量买入"
              titleTip={CAPITAL_METRIC_TIPS.clippedBuyParticipation}
              value={metrics.clippedBuyParticipation.toLocaleString()}
            />
            <MetricCard
              title="参与率缩量卖出"
              titleTip={CAPITAL_METRIC_TIPS.clippedSellParticipation}
              value={metrics.clippedSellParticipation.toLocaleString()}
            />
          </Box>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="仓位与资金利用率"
        tip={CAPITAL_SECTION_TIPS.utilization}
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="平均持仓数"
            titleTip={CAPITAL_METRIC_TIPS.avgOpenPositions}
            value={`${metrics.avgOpenPositions} / ${metrics.peakPositions}`}
          />
          <MetricCard
            title="满仓天数占比"
            titleTip={CAPITAL_METRIC_TIPS.fullExposureDaysRatio}
            value={`${metrics.fullExposureDaysRatio}%`}
          />
          <MetricCard
            title="平均现金占比"
            titleTip={CAPITAL_METRIC_TIPS.avgCashRatio}
            value={`${metrics.avgCashRatio}%`}
          />
          <MetricCard
            title="资金利用率"
            titleTip={CAPITAL_METRIC_TIPS.capitalUtilization}
            value={`${metrics.capitalUtilizationRatio}%`}
          />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="风险结构"
        tip={CAPITAL_SECTION_TIPS.risk}
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="最大回撤"
            titleTip={CAPITAL_METRIC_TIPS.maxDrawdown}
            value={`${metrics.maxDrawdownPct}%`}
          />
          <MetricCard
            title="最大回撤持续天数"
            titleTip={CAPITAL_METRIC_TIPS.maxDrawdownDuration}
            value={`${metrics.maxDrawdownDurationDays} 天`}
          />
          <MetricCard
            title="最长连续亏损"
            titleTip={CAPITAL_METRIC_TIPS.maxLossStreak}
            value={`${metrics.maxLossStreak} 笔`}
          />
          <MetricCard
            title="Top3 单笔亏损"
            titleTip={CAPITAL_METRIC_TIPS.worstTradePnls}
            value={metrics.worstTradePnls.map((value) => formatReportMoney(value)).join(' / ')}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              回撤曲线
            </Typography>
            <NtqHelpTooltip title={CAPITAL_CHART_TIPS.drawdownCurve} />
          </Stack>
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
        tip={CAPITAL_SECTION_TIPS.concentration}
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="触发股票数"
            titleTip={CAPITAL_METRIC_TIPS.stockCount}
            value={metrics.stockCount.toLocaleString()}
          />
          <MetricCard
            title="每股平均交易次数"
            titleTip={CAPITAL_METRIC_TIPS.avgTradesPerStock}
            value={metrics.avgTradesPerStock.toFixed(2)}
          />
          <MetricCard
            title="前 5 股票收益贡献占比"
            titleTip={CAPITAL_METRIC_TIPS.top5ContributionRatio}
            value={`${metrics.top5ContributionRatio}%`}
          />
          <MetricCard
            title="股票收益离散系数（CV）"
            titleTip={CAPITAL_METRIC_TIPS.stockPnlCv}
            value={metrics.stockPnlCv}
          />
        </Box>
      </SectionBlock>
    </Stack>
  );
}

export default CapitalAllocationReport;
