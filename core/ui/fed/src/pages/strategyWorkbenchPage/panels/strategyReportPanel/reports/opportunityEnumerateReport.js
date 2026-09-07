import React from 'react';
import { Stack, Typography } from '@mui/material';
import ChartPanel from 'components/chartPanel/chartPanel';
import MetricCard from 'components/metricCard/metricCard';
import MetricGrid from 'components/metricGrid/metricGrid';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import {
  ENUM_CHART_TIPS,
  ENUM_METRIC_TIPS,
  ENUM_SECTION_TIPS,
  REPORT_STOCK_GRID_TIPS,
} from '../reportMetricTips';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import ReportStockGridSection from '../components/reportStockGridSection';
import { useReportStockSearch } from '../hooks/useReportStockSearch';
import { STOCK_NAME_COLUMN, stockCodeColumn } from '../lib/reportStockColumns';
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
  onStockSelect,
  stockLinkEnabled = false,
}) {
  const { stockSearch, setStockSearch, filteredRows } = useReportStockSearch(stockRows);

  const avail = metrics?._availability ?? {
    overview: false,
    stockStats: false,
    distribution: false,
    timing: false,
    tradability: false,
  };

  const stockColumns = [
    stockCodeColumn({ onStockSelect, stockLinkEnabled }),
    STOCK_NAME_COLUMN,
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

  return (
    <Stack spacing={1.25}>
      {!hideTitle ? (
        <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>
      ) : null}

      {showStockGrid ? (
        <ReportStockGridSection
          loading={stockGridLoading}
          overlay={stockGridOverlay}
          filteredRows={filteredRows}
          title="逐股样本"
          tip={stockGridTip}
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          columns={stockColumns}
          sortingMode="client"
          initialSortModel={[{ field: 'opportunities', sort: 'desc' }]}
        />
      ) : null}

      <SectionBlock
        title="机会总体统计"
        tip={ENUM_SECTION_TIPS.overview}
      >
        {avail.overview ? (
          <MetricGrid>
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
          </MetricGrid>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="股票机会统计"
        tip={ENUM_SECTION_TIPS.stockStats}
      >
        {avail.stockStats ? (
          <MetricGrid>
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
          </MetricGrid>
        ) : <ReportUnavailableHint />}
        <ChartPanel
          title="每股机会数分布"
          tip={ENUM_CHART_TIPS.opportunityDistribution}
          option={avail.distribution ? buildStockDistributionOption(metrics) : null}
          height={170}
          fallback={<ReportUnavailableHint />}
          sx={{ mt: avail.stockStats ? 1 : 0 }}
        />
      </SectionBlock>

      <SectionBlock
        title="涨跌停可成交性"
        tip={ENUM_SECTION_TIPS.tradability}
      >
        {avail.tradability ? (
          <MetricGrid>
            <MetricCard
              title="涨停无法买入"
              titleTip={ENUM_METRIC_TIPS.limitUpBuy}
              value={`${metrics.buyAtLimitUpCount.toLocaleString()} / ${metrics.buyTradabilitySampleCount.toLocaleString()}`}
              hint={`占比 ${metrics.limitUpBuyRatio}%`}
            />
            <MetricCard
              title="跌停无法卖出"
              titleTip={ENUM_METRIC_TIPS.limitDownSell}
              value={`${metrics.sellAtLimitDownCount.toLocaleString()} / ${metrics.sellTradabilitySampleCount.toLocaleString()}`}
              hint={`占比 ${metrics.limitDownSellRatio}%`}
            />
          </MetricGrid>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="机会出现"
        tip={ENUM_SECTION_TIPS.timing}
      >
        {avail.timing ? (
          <Stack spacing={1}>
            <MetricGrid>
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
            </MetricGrid>
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
