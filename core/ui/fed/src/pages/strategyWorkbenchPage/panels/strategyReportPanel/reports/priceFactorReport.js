import React, { useMemo, useState } from 'react';
import { Box, Link, Stack, Typography } from '@mui/material';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import ReactECharts from 'echarts-for-react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import {
  PRICE_CHART_TIPS,
  PRICE_METRIC_TIPS,
  PRICE_SECTION_TIPS,
  REPORT_STOCK_GRID_TIPS,
} from '../reportMetricTips';
import { formatReportMoney } from '../lib/formatReportMoney';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LABEL_SM,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_GRID_ROI_BUCKET,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
  reportChartSignedBarData,
  reportChartRoiBucketBarData,
} from '../lib/reportChartsTheme';

function tooltipPrimaryValue(point) {
  const raw = point?.data;
  if (raw != null && typeof raw === 'object' && Object.prototype.hasOwnProperty.call(raw, 'value')) {
    return raw.value;
  }
  return raw;
}

function buildRoiDistributionOption(metrics) {
  return {
    animation: false,
    grid: { ...REPORT_CHART_GRID_BASE, left: 30 },
    xAxis: {
      type: 'category',
      data: metrics.roiPercentileLabels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: REPORT_CHART_AXIS_LABEL,
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...REPORT_CHART_AXIS_LABEL, formatter: '{value}%' },
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'bar',
        data: reportChartSignedBarData(metrics.roiPercentileValues),
        barMaxWidth: 28,
      },
    ],
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        const val = tooltipPrimaryValue(point);
        return `${point.axisValue}<br/>收益率（ROI）：${val}%`;
      },
    },
  };
}

function buildRoiBucketOption(metrics) {
  return {
    animation: false,
    grid: REPORT_CHART_GRID_ROI_BUCKET,
    xAxis: {
      type: 'category',
      data: metrics.roiBucketLabels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: { ...REPORT_CHART_AXIS_LABEL_SM, interval: 0, rotate: 25 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: REPORT_CHART_AXIS_LABEL,
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'bar',
        data: reportChartRoiBucketBarData(metrics.roiBucketCounts, metrics.roiBucketLabels),
        barMaxWidth: 24,
      },
    ],
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>投资次数：${tooltipPrimaryValue(point)}`;
      },
    },
  };
}

function PriceFactorReport({
  metrics,
  stockRows,
  title = '价格回测报告',
  showStockGrid = true,
  stockGridOverlay = null,
  priceRefStockTotal,
  stockGridLoading = false,
  hideTitle = false,
  onStockSelect,
  stockLinkEnabled = false,
}) {
  const [stockSearch, setStockSearch] = useState('');

  const avail = metrics?._availability ?? {
    overview: false,
    sampleCoverage: false,
    profitBasics: false,
    roiPercentileViz: false,
    roiBucketViz: false,
    executionSkips: false,
  };

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

  const stockColumns = useMemo(() => [
    {
      field: 'stockCode',
      headerName: '代码',
      flex: 1,
      minWidth: 120,
      renderCell: (params) => {
        const code = params.value;
        if (!stockLinkEnabled || typeof onStockSelect !== 'function') {
          return code;
        }
        return (
          <Link
            component="button"
            type="button"
            underline="hover"
            onClick={(e) => {
              e.stopPropagation();
              onStockSelect(params.row);
            }}
            sx={{ font: 'inherit', textAlign: 'left' }}
          >
            {code}
          </Link>
        );
      },
    },
    { field: 'stockName', headerName: '名称', flex: 1, minWidth: 120 },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
    {
      field: 'avgRoi',
      headerName: '平均 ROI',
      width: 120,
      valueFormatter: (params) => {
        const v = Number(params.value);
        if (!Number.isFinite(v)) return '—';
        return `${v > 0 ? '+' : ''}${v}%`;
      },
    },
    {
      field: 'avgDurationDays',
      headerName: '平均交易时长',
      width: 130,
      valueFormatter: (params) => `${params.value} 天`,
    },
    {
      field: 'expirationRatio',
      headerName: '过期比例',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
  ], [onStockSelect, stockLinkEnabled]);

  const stockGridTip = [
    REPORT_STOCK_GRID_TIPS.price,
    typeof priceRefStockTotal === 'number' && priceRefStockTotal > 0
      ? `当前共 ${priceRefStockTotal} 只股票。`
      : '',
  ].filter(Boolean).join(' ');

  if (!metrics || typeof metrics !== 'object') {
    return <ReportUnavailableHint />;
  }

  const showStockGridTable = Boolean(stockGridOverlay || filteredRows.length > 0);

  const volCardHint = (() => {
    if (!avail.roiPercentileViz) return '';
    if (Number.isFinite(metrics.roiStdPct)) {
      return [
        Number.isFinite(metrics.roiP50) ? `P50 ${metrics.roiP50}%` : '',
        Number.isFinite(metrics.roiIqr) ? `IQR ${metrics.roiIqr}%` : '',
      ].filter(Boolean).join(' · ');
    }
    return [
      Number.isFinite(metrics.roiIqr) ? `IQR ${metrics.roiIqr}%` : '',
      metrics.roiConclusion || '',
    ].filter(Boolean).join(' · ');
  })();

  return (
    <Stack spacing={1.25}>
      {!hideTitle ? (
        <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>
      ) : null}

      {showStockGrid ? (
        <Box sx={{ position: 'relative' }}>
          {stockGridLoading ? (
            <InlineLoadingState block compact message="正在加载逐股数据…" />
          ) : (
            <>
              {stockGridOverlay}
              {showStockGridTable ? (
                <ReportStockSampleGrid
                  title="逐股样本"
                  tip={stockGridTip}
                  searchValue={stockSearch}
                  onSearchChange={setStockSearch}
                  rows={filteredRows}
                  columns={stockColumns}
                  sortingMode="client"
                  initialSortModel={[{ field: 'winRate', sort: 'desc' }]}
                />
              ) : <ReportUnavailableHint />}
            </>
          )}
        </Box>
      ) : null}

      <SectionBlock
        title="回测总体"
        tip={PRICE_SECTION_TIPS.overview}
      >
        {avail.overview ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard title="胜率" titleTip={PRICE_METRIC_TIPS.winRate} value={`${metrics.winRate}%`} />
            <MetricCard
              title="平均每笔收益率（ROI）"
              titleTip={PRICE_METRIC_TIPS.avgRoi}
              value={`${metrics.avgRoi}%`}
            />
            <MetricCard
              title="平均持有时长"
              titleTip={PRICE_METRIC_TIPS.avgDurationDays}
              value={`${metrics.avgDurationDays} 天`}
            />
            <MetricCard
              title="年化收益（自然日）"
              titleTip={PRICE_METRIC_TIPS.annualReturn}
              value={`${metrics.annualReturn}%`}
            />
          </Box>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="样本与覆盖"
        tip={PRICE_SECTION_TIPS.sampleCoverage}
      >
        {avail.sampleCoverage ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="总投资次数"
              titleTip={PRICE_METRIC_TIPS.totalInvestments}
              value={metrics.totalInvestments.toLocaleString()}
            />
            <MetricCard
              title="产生机会股票数"
              titleTip={PRICE_METRIC_TIPS.stocksWithOpportunities}
              value={metrics.stocksWithOpportunities.toLocaleString()}
            />
            <MetricCard
              title="每股平均投资次数"
              titleTip={PRICE_METRIC_TIPS.avgInvestmentsPerStock}
              value={metrics.avgInvestmentsPerStock.toFixed(2)}
            />
            <MetricCard
              title="未完成持仓数"
              titleTip={PRICE_METRIC_TIPS.totalOpenInvestments}
              value={metrics.totalOpenInvestments.toLocaleString()}
            />
          </Box>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="成交跳过统计"
        tip={PRICE_SECTION_TIPS.executionSkips}
      >
        {avail.executionSkips ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="涨停跳过买入"
              titleTip={PRICE_METRIC_TIPS.skippedBuyAtLimitUp}
              value={metrics.skippedBuyAtLimitUp.toLocaleString()}
            />
            <MetricCard
              title="跌停跳过卖出"
              titleTip={PRICE_METRIC_TIPS.skippedSellAtLimitDown}
              value={metrics.skippedSellAtLimitDown.toLocaleString()}
            />
            <MetricCard
              title="状态跳过投资"
              titleTip={PRICE_METRIC_TIPS.skippedStockStatus}
              value={metrics.skippedStockStatus.toLocaleString()}
            />
          </Box>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="盈亏结构（含收益率分位）"
        tip={PRICE_SECTION_TIPS.profitStructure}
      >
        {avail.profitBasics ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="盈亏次数"
              titleTip={PRICE_METRIC_TIPS.winLossCount}
              value={`${metrics.totalWinInvestments} / ${metrics.totalLossInvestments}`}
              hint="赢单 / 亏单"
            />
            <MetricCard
              title="每笔平均盈利"
              titleTip={PRICE_METRIC_TIPS.avgProfitPerInvestment}
              value={formatReportMoney(metrics.avgProfitPerInvestment)}
            />
            <MetricCard
              title="每股平均盈利"
              titleTip={PRICE_METRIC_TIPS.avgProfitPerStock}
              value={formatReportMoney(metrics.avgProfitPerStock)}
            />
            {avail.roiPercentileViz ? (
              <MetricCard
                title="收益率（ROI）波动"
                titleTip={PRICE_METRIC_TIPS.roiVolatility}
                value={
                  Number.isFinite(metrics.roiStdPct)
                    ? `标准差 ${metrics.roiStdPct}%（样本）`
                    : `P25 ${metrics.roiP25}% · P50 ${metrics.roiP50}% · P75 ${metrics.roiP75}%`
                }
                hint={volCardHint}
              />
            ) : null}
          </Box>
        ) : <ReportUnavailableHint />}
        {!avail.roiPercentileViz ? (
          <Box sx={{ mt: avail.profitBasics ? 1 : 0 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              {PRICE_CHART_TIPS.roiPercentileUnavailable}
            </Typography>
            <ReportUnavailableHint />
          </Box>
        ) : (
          <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: 1 }}>
            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
              <Typography variant="caption" color="text.secondary">
                收益率（ROI）分位图
              </Typography>
              <NtqHelpTooltip title={PRICE_CHART_TIPS.roiPercentileCaption} />
            </Stack>
            <ReactECharts
              option={buildRoiDistributionOption(metrics)}
              style={{ height: 170, width: '100%' }}
              notMerge
              lazyUpdate
            />
          </Box>
        )}
        {!avail.roiBucketViz ? (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              {PRICE_CHART_TIPS.roiBucketUnavailable}
            </Typography>
            <ReportUnavailableHint />
          </Box>
        ) : (
          <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: 1 }}>
            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
              <Typography variant="caption" color="text.secondary">
                收益率（ROI）分布
              </Typography>
              <NtqHelpTooltip title={PRICE_CHART_TIPS.roiBucketCaption} />
            </Stack>
            <ReactECharts
              option={buildRoiBucketOption(metrics)}
              style={{ height: 190, width: '100%' }}
              notMerge
              lazyUpdate
            />
          </Box>
        )}
      </SectionBlock>
    </Stack>
  );
}

export default PriceFactorReport;
