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
  return {
    animation: false,
    grid: { left: 30, right: 10, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: metrics.percentileLabels,
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
        data: metrics.percentileValues,
        barMaxWidth: 28,
        itemStyle: { color: '#5B8FF9', borderRadius: [4, 4, 0, 0] },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>每股机会数：${point.data}`;
      },
    },
  };
}

function OpportunityEnumrateReport({ metrics, title = '枚举核心结论（草图）', showStockGrid = true }) {
  const [stockSearch, setStockSearch] = useState('');
  const [stockSortBy, setStockSortBy] = useState('default');

  const stockRows = useMemo(() => buildEnumSampleStockRows(metrics || {}), [metrics]);

  const filteredAndSortedRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    const filtered = keyword
      ? stockRows.filter((row) => (
        row.stockCode.toLowerCase().includes(keyword) || row.stockName.toLowerCase().includes(keyword)
      ))
      : stockRows;
    const sorted = [...filtered];
    if (stockSortBy === 'opportunitiesDesc') sorted.sort((a, b) => b.opportunities - a.opportunities);
    if (stockSortBy === 'completionDesc') sorted.sort((a, b) => b.completionRate - a.completionRate);
    if (stockSortBy === 'spanAsc') sorted.sort((a, b) => a.triggerSpanDays - b.triggerSpanDays);
    return sorted.slice(0, 10);
  }, [stockRows, stockSearch, stockSortBy]);

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
            title="股票触发机会的比例"
            value={`${metrics.triggerStocks} / ${metrics.totalStocks} (${metrics.triggerRatio}%)`}
          />
          <MetricCard
            title="平均每股产生机会数"
            value={metrics.avgPerStock.toFixed(2)}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            每股机会数分位图（10% / 20% / 30% / 40% / 50% / 60% / 70% / 80% / 90%）
          </Typography>
          <ReactECharts
            option={buildStockDistributionOption(metrics)}
            style={{ height: 170, width: '100%' }}
            notMerge
            lazyUpdate
          />
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
