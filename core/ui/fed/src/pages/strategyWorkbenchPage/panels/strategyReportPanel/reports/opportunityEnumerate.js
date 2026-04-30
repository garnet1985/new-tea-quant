import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import { buildEnumSampleStockRows } from '../../../mocks/strategyReportSampleRows';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';

const ENUM_STOCK_SORT_MENU = [
  { value: 'default', label: '接口顺序' },
  { value: 'opportunitiesDesc', label: '机会数（高到低）' },
  { value: 'completionDesc', label: '完整度（高到低）' },
  { value: 'spanAsc', label: '平均机会间隔（低到高）' },
];

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
    grid: { left: 30, right: 10, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: xData,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 11 },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
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
  title = '枚举核心结论（草图）',
  showStockGrid = true,
}) {
  const [stockSearch, setStockSearch] = useState('');
  const [stockSortBy, setStockSortBy] = useState('default');

  const derivedStockRows = useMemo(() => {
    if (Array.isArray(stockRows) && stockRows.length > 0) return stockRows;
    return buildEnumSampleStockRows(metrics || {});
  }, [metrics, stockRows]);

  const filteredAndSortedRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    const filtered = keyword
      ? derivedStockRows.filter((row) => (
        row.stockCode.toLowerCase().includes(keyword) || row.stockName.toLowerCase().includes(keyword)
      ))
      : derivedStockRows;
    const sorted = [...filtered];
    if (stockSortBy === 'opportunitiesDesc') sorted.sort((a, b) => b.opportunities - a.opportunities);
    if (stockSortBy === 'completionDesc') sorted.sort((a, b) => b.completionRate - a.completionRate);
    if (stockSortBy === 'spanAsc') sorted.sort((a, b) => a.triggerSpanDays - b.triggerSpanDays);
    return sorted.slice(0, 10);
  }, [derivedStockRows, stockSearch, stockSortBy]);

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
  const hasDistributionData = Array.isArray(metrics?.opportunityCountLabels)
    && metrics.opportunityCountLabels.length > 0;
  const distributionTip = opportunityCountBucketCount > 0
    ? `每股机会数分布图（${opportunityCountMin}~${opportunityCountMax}，近似 ${opportunityCountBucketCount} 等分；显示：股票数（占比））`
    : '每股机会数分布图（显示：股票数（占比））';

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      {showStockGrid ? (
        <ReportStockSampleGrid
          title="样本股票（最多 10 只）"
          tip="用于快速查看枚举阶段的单股机会覆盖情况，支持搜索和核心参数排序。"
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          sortValue={stockSortBy}
          onSortChange={setStockSortBy}
          sortSelectLabelId="enum-stock-sort-label"
          sortMenuItems={ENUM_STOCK_SORT_MENU}
          rows={filteredAndSortedRows}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="机会总体统计"
        tip="用于判断当前策略是否给出足够机会，以及机会完成质量是否达标。"
      >
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
      </SectionBlock>

      <SectionBlock
        title="股票机会统计"
        tip="用于判断机会是否集中在少数股票，以及每股机会分布的分位结构。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="触发机会的股票占比"
            value={`${metrics.triggerStocks} / ${metrics.totalStocks} (${metrics.triggerRatio}%)`}
          />
          <MetricCard
            title="平均每股产生机会数"
            value={metrics.avgPerStock.toFixed(2)}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            {distributionTip}
          </Typography>
          {hasDistributionData ? (
            <ReactECharts
              option={buildStockDistributionOption(metrics)}
              style={{ height: 170, width: '100%' }}
              notMerge
              lazyUpdate
            />
          ) : (
            <Typography variant="caption" color="text.secondary">
              暂无真实区间分布数据（等待枚举报告写入 opportunityCount* 字段）。
            </Typography>
          )}
        </Box>
      </SectionBlock>

      <SectionBlock
        title="机会出现"
        tip="用于衡量机会生成节奏是否稳定，避免机会扎堆导致资金使用不均。"
      >
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
      </SectionBlock>
    </Stack>
  );
}

export default OpportunityEnumrateReport;
