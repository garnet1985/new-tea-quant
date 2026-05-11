import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import ReportUnavailableHint from '../components/ReportUnavailableHint';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_SPLIT_LINE,
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
        data: yData,
        barMaxWidth: 28,
        itemStyle: { color: '#5B8FF9', borderRadius: [4, 4, 0, 0] },
        label: {
          show: true,
          position: 'top',
          fontSize: 10,
          color: '#5F6368',
          formatter: (params) => {
            const idx = Number(params?.dataIndex ?? -1);
            const count = idx >= 0 ? Number(countData[idx] ?? 0) : 0;
            const ratio = Number(params?.data ?? 0);
            return `${count}（${ratio}%）`;
          },
        },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        const idx = Number(point?.dataIndex ?? -1);
        const count = idx >= 0 ? Number(countData[idx] ?? 0) : 0;
        return `${point.axisValue} 次机会<br/>股票数：${count}（${point.data}%）`;
      },
    },
  };
}

function OpportunityEnumrateReport({
  metrics,
  stockRows,
  title = '枚举核心结论',
  showStockGrid = true,
  stockGridOverlay = null,
  reportRefUrl = '',
  enumRefStockTotal,
  stockGridLoading = false,
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
  const opportunityCountMin = Number(metrics?.opportunityCountMin ?? 0);
  const opportunityCountMax = Number(metrics?.opportunityCountMax ?? 0);
  const opportunityCountBucketCount = Number(metrics?.opportunityCountBucketCount ?? 0);
  const distributionTip = avail.distribution && opportunityCountBucketCount > 0
    ? `每股机会数分布图（${opportunityCountMin}~${opportunityCountMax}，近似 ${opportunityCountBucketCount} 等分；显示：股票数（占比））`
    : '每股机会数分布图（显示：股票数（占比））';

  const stockGridTip = [
    '用于查看枚举阶段的单股指标；支持搜索、表头排序与底部分页（数据一次加载后在前端分页）。',
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
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      {typeof reportRefUrl === 'string' && reportRefUrl.trim() !== '' ? (
        <Typography variant="caption" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
          逐股数据：
          {reportRefUrl}
        </Typography>
      ) : null}

      {showStockGrid ? (
        <Box sx={{ position: 'relative' }}>
          {stockGridLoading ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
              正在加载逐股数据…
            </Typography>
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
        tip="用于判断当前策略是否给出足够机会，以及机会完成质量是否达标。"
      >
        {avail.overview ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="机会总数"
              value={`${metrics.totalOpportunities.toLocaleString()}（共 ${metrics.totalStocks.toLocaleString()} 只股票）`}
            />
            <MetricCard
              title="机会完整度"
              value={`${metrics.completedCount.toLocaleString()} / ${metrics.totalOpportunities.toLocaleString()} (${metrics.completedRatio}%)`}
            />
          </Box>
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="股票机会统计"
        tip="用于判断机会是否集中在少数股票，以及每股机会分布的分位结构。"
      >
        {avail.stockStats ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="触发机会的股票占比"
              value={`${metrics.triggerStocks} / ${metrics.totalStocks} (${metrics.triggerRatio}%)`}
            />
            <MetricCard
              title="平均每股产生机会数"
              value={Number(metrics.avgPerStock).toFixed(2)}
            />
          </Box>
        ) : <ReportUnavailableHint />}
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: avail.stockStats ? 1 : 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            {distributionTip}
          </Typography>
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
        tip="用于衡量机会生成节奏是否稳定，避免机会扎堆导致资金使用不均。"
      >
        {avail.timing ? (
          <Stack spacing={1}>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
              <MetricCard title="平均每股机会间隔" value={`${metrics.meanGap} 天`} />
              <MetricCard title="平均每股机会持续（天）" value={`${metrics.meanDuration} 天`} />
            </Box>
            <MetricCard
              title="机会分散度"
              value={`SD ${metrics.stdGap} 天`}
              hint={`CV ${metrics.cv} · ${metrics.dispersionConclusion}`}
            />
          </Stack>
        ) : <ReportUnavailableHint />}
      </SectionBlock>
    </Stack>
  );
}

export default OpportunityEnumrateReport;
