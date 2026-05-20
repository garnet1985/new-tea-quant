import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import {
  ENUM_CHART_TIPS,
  ENUM_METRIC_TIPS,
  ENUM_SECTION_TIPS,
  REPORT_STOCK_GRID_TIPS,
} from '../reportMetricTips';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_DATA_LABEL,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
  reportChartSignedBarData,
} from '../lib/reportChartsTheme';

function buildStockDistributionOption(metrics) {
  const xData = Array.isArray(metrics?.opportunityCountLabels) ? metrics.opportunityCountLabels : [];
  const countData = Array.isArray(metrics?.opportunityCountStockCounts)
    ? metrics.opportunityCountStockCounts
    : [];
  const yData = Array.isArray(metrics?.opportunityCountStockRatios)
    ? metrics.opportunityCountStockRatios
    : [];
  return {
    animation: false,
    grid: { ...REPORT_CHART_GRID_BASE, left: 30 },
    xAxis: {
      type: 'category',
      data: xData,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: REPORT_CHART_AXIS_LABEL,
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
        data: reportChartSignedBarData(yData),
        barMaxWidth: 28,
        label: {
          show: true,
          position: 'top',
          ...REPORT_CHART_DATA_LABEL,
          formatter: (params) => {
            const idx = Number(params?.dataIndex ?? -1);
            const count = idx >= 0 ? Number(countData[idx] ?? 0) : 0;
            const ratio = Number(params?.value ?? params?.data?.value ?? params?.data ?? 0);
            return `${count}（${ratio}%）`;
          },
        },
      },
    ],
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        const idx = Number(point?.dataIndex ?? -1);
        const count = idx >= 0 ? Number(countData[idx] ?? 0) : 0;
        const ratio = Number(point?.value ?? point?.data?.value ?? point?.data ?? 0);
        return `${point.axisValue} 次机会<br/>股票数：${count}（${ratio}%）`;
      },
    },
  };
}

function OpportunityEnumrateReport({
  metrics,
  stockRows,
  title = '枚举机会报告',
  showStockGrid = true,
  stockGridOverlay = null,
  enumRefStockTotal,
  stockGridLoading = false,
  hideTitle = false,
}) {
  const [stockSearch, setStockSearch] = useState('');

  const avail = metrics?._availability ?? {
    overview: false,
    stockStats: false,
    distribution: false,
    timing: false,
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

  const stockColumns = [
    { field: 'stockCode', headerName: '代码', flex: 1, minWidth: 120 },
    { field: 'stockName', headerName: '名称', flex: 1, minWidth: 120 },
    {
      field: 'opportunities',
      headerName: '机会数',
      width: 110,
      valueFormatter: (params) => `${params.value} 个`,
    },
    {
      field: 'completionRate',
      headerName: '完整度',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
    {
      field: 'triggerSpanDays',
      headerName: '平均机会间隔',
      width: 130,
      valueFormatter: (params) => `${params.value} 天`,
    },
  ];
  const stockGridTip = [
    REPORT_STOCK_GRID_TIPS.enum,
    typeof enumRefStockTotal === 'number' && enumRefStockTotal > 0
      ? `当前共 ${enumRefStockTotal} 只股票。`
      : '',
  ].filter(Boolean).join(' ');

  if (!metrics || typeof metrics !== 'object') {
    return <ReportUnavailableHint />;
  }

  const showStockGridTable = Boolean(stockGridOverlay || filteredRows.length > 0);

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
                  initialSortModel={[{ field: 'opportunities', sort: 'desc' }]}
                />
              ) : <ReportUnavailableHint />}
            </>
          )}
        </Box>
      ) : null}

      <SectionBlock
        title="机会总体统计"
        tip={ENUM_SECTION_TIPS.overview}
      >
        {avail.overview ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="机会总数"
              titleTip={ENUM_METRIC_TIPS.totalOpportunities}
              value={`${metrics.totalOpportunities.toLocaleString()}（共 ${metrics.totalStocks.toLocaleString()} 只股票）`}
            />
            <MetricCard
              title="机会完整度"
              titleTip={ENUM_METRIC_TIPS.completeness}
              value={`${metrics.completedCount.toLocaleString()} / ${metrics.totalOpportunities.toLocaleString()} (${metrics.completedRatio}%)`}
            />
          </Box>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="股票机会统计"
        tip={ENUM_SECTION_TIPS.stockStats}
      >
        {avail.stockStats ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="触发机会的股票占比"
              titleTip={ENUM_METRIC_TIPS.triggerStocksRatio}
              value={`${metrics.triggerStocks} / ${metrics.totalStocks} (${metrics.triggerRatio}%)`}
            />
            <MetricCard
              title="平均每股产生机会数"
              titleTip={ENUM_METRIC_TIPS.avgPerStock}
              value={Number(metrics.avgPerStock).toFixed(2)}
            />
          </Box>
        ) : <ReportUnavailableHint />}
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: avail.stockStats ? 1 : 0 }}>
          <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              每股机会数分布
            </Typography>
            <NtqHelpTooltip title={ENUM_CHART_TIPS.opportunityDistribution} />
          </Stack>
          {avail.distribution ? (
            <ReactECharts
              option={buildStockDistributionOption(metrics)}
              style={{ height: 170, width: '100%' }}
              notMerge
              lazyUpdate
            />
          ) : <ReportUnavailableHint />}
        </Box>
      </SectionBlock>

      <SectionBlock
        title="机会出现"
        tip={ENUM_SECTION_TIPS.timing}
      >
        {avail.timing ? (
          <Stack spacing={1}>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
              <MetricCard
                title="平均每股机会间隔"
                titleTip={ENUM_METRIC_TIPS.meanGap}
                value={`${metrics.meanGap} 天`}
              />
              <MetricCard
                title="平均每股机会持续（天）"
                titleTip={ENUM_METRIC_TIPS.meanDuration}
                value={`${metrics.meanDuration} 天`}
              />
            </Box>
            <MetricCard
              title="机会分散度"
              titleTip={ENUM_METRIC_TIPS.dispersion}
              value={Number.isFinite(Number(metrics.stdGap))
                ? `SD ${metrics.stdGap} 天`
                : '—'}
              hint={[
                Number.isFinite(Number(metrics.cv)) ? `CV ${metrics.cv}` : null,
                (metrics.dispersionConclusion && String(metrics.dispersionConclusion).trim()) || null,
              ].filter(Boolean).join(' · ') || undefined}
            />
          </Stack>
        ) : <ReportUnavailableHint />}
      </SectionBlock>
    </Stack>
  );
}

export default OpportunityEnumrateReport;
