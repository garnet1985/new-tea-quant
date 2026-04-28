import React, { useMemo, useState } from 'react';
import { Box, Button, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import { buildPriceSampleStockRows } from '../../../mocks/strategyReportSampleRows';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import StockKlineDialog from '../components/stockKlineDialog';

const PRICE_STOCK_SORT_MENU = [
  { value: 'default', label: '接口顺序' },
  { value: 'winRateDesc', label: '胜率（高到低）' },
  { value: 'roiDesc', label: 'ROI（高到低）' },
  { value: 'holdDaysAsc', label: '平均投资天数（低到高）' },
];

const EMPTY_METRICS_BASE = {
  totalInvestments: 0,
  winRate: 0,
  avgRoi: 0,
  avgDurationDays: 0,
};

function buildRoiDistributionOption(metrics) {
  return {
    animation: false,
    grid: { left: 30, right: 10, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: metrics.roiPercentileLabels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
    },
    series: [
      {
        type: 'bar',
        data: metrics.roiPercentileValues,
        barMaxWidth: 28,
        itemStyle: { color: '#36A2EB', borderRadius: [4, 4, 0, 0] },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>ROI：${point.data}%`;
      },
    },
  };
}

function buildRoiBucketOption(metrics) {
  return {
    animation: false,
    grid: { left: 30, right: 10, top: 20, bottom: 50 },
    xAxis: {
      type: 'category',
      data: metrics.roiBucketLabels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 10, interval: 0, rotate: 25 },
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
        data: metrics.roiBucketCounts,
        barMaxWidth: 24,
        itemStyle: { color: '#7A8DF5', borderRadius: [4, 4, 0, 0] },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>投资次数：${point.data}`;
      },
    },
  };
}

function PriceFactorReport({ metrics, title = '价格回测报告（草图）', showStockGrid = true }) {
  const [stockSearch, setStockSearch] = useState('');
  const [stockSortBy, setStockSortBy] = useState('default');
  const [selectedStock, setSelectedStock] = useState(null);

  const stockRows = useMemo(() => {
    const base = metrics || EMPTY_METRICS_BASE;
    return buildPriceSampleStockRows(base);
  }, [metrics]);

  const filteredAndSortedRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    const filtered = keyword
      ? stockRows.filter((row) => (
        row.stockCode.toLowerCase().includes(keyword) || row.stockName.toLowerCase().includes(keyword)
      ))
      : stockRows;
    const sorted = [...filtered];
    if (stockSortBy === 'winRateDesc') sorted.sort((a, b) => b.winRate - a.winRate);
    if (stockSortBy === 'roiDesc') sorted.sort((a, b) => b.roi - a.roi);
    if (stockSortBy === 'holdDaysAsc') sorted.sort((a, b) => a.holdDays - b.holdDays);
    return sorted.slice(0, 10);
  }, [stockRows, stockSearch, stockSortBy]);

  const stockColumns = useMemo(() => [
    {
      field: 'stockCode',
      headerName: '代码',
      flex: 1,
      minWidth: 120,
      renderCell: (params) => (
        <Button
          variant="text"
          size="small"
          sx={{ minWidth: 0, px: 0.25 }}
          onClick={() => setSelectedStock(params.row)}
        >
          {params.value}
        </Button>
      ),
    },
    { field: 'stockName', headerName: '名称', flex: 1, minWidth: 120 },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
    {
      field: 'roi',
      headerName: 'ROI',
      width: 110,
      valueFormatter: (params) => `${params.value > 0 ? '+' : ''}${params.value}%`,
    },
    {
      field: 'holdDays',
      headerName: '平均投资天数',
      width: 110,
      valueFormatter: (params) => `${params.value} 天`,
    },
  ], []);

  if (!metrics) {
    return (
      <Typography variant="body2" color="text.secondary">
        暂无价格回测结果。
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      {showStockGrid ? (
        <ReportStockSampleGrid
          title="样本股票（最多 10 只）"
          tip="用于快速查看本次价格回测中代表性股票的核心表现，支持搜索和核心参数排序。点击代码可查看 K 线与买卖点。"
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          sortValue={stockSortBy}
          onSortChange={setStockSortBy}
          sortSelectLabelId="price-stock-sort-label"
          sortMenuItems={PRICE_STOCK_SORT_MENU}
          rows={filteredAndSortedRows}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="回测总体"
        tip="用于判断信号层是否具备正向收益，且收益效率是否可接受。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="胜率" value={`${metrics.winRate}%`} />
          <MetricCard title="平均每笔 ROI" value={`${metrics.avgRoi}%`} />
          <MetricCard title="平均持有时长" value={`${metrics.avgDurationDays} 天`} />
          <MetricCard title="年化收益（自然日）" value={`${metrics.annualReturn}%`} />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="样本与覆盖"
        tip="用于确认结果是否来自足够样本，避免小样本导致结论失真。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="总投资次数" value={metrics.totalInvestments.toLocaleString()} />
          <MetricCard title="产生机会股票数" value={metrics.stocksWithOpportunities.toLocaleString()} />
          <MetricCard title="每股平均投资次数" value={metrics.avgInvestmentsPerStock.toFixed(2)} />
          <MetricCard title="未完成持仓数" value={metrics.totalOpenInvestments.toLocaleString()} />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="盈亏结构（含 ROI 分位）"
        tip="用于观察收益分布是否健康，避免只靠少数大盈利机会拉高均值。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard
            title="盈亏次数"
            value={`${metrics.totalWinInvestments} / ${metrics.totalLossInvestments}`}
            hint="赢单 / 亏单"
          />
          <MetricCard title="每笔平均盈利" value={metrics.avgProfitPerInvestment.toLocaleString()} />
          <MetricCard title="每股平均盈利" value={metrics.avgProfitPerStock.toLocaleString()} />
          <MetricCard
            title="ROI 分位摘要"
            value={`P25 ${metrics.roiP25}% · P50 ${metrics.roiP50}% · P75 ${metrics.roiP75}%`}
            hint={`IQR ${metrics.roiIqr}% · ${metrics.roiConclusion}`}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            ROI 分位图（10% / 20% / 30% / 40% / 50% / 60% / 70% / 80% / 90%）
          </Typography>
          <ReactECharts
            option={buildRoiDistributionOption(metrics)}
            style={{ height: 170, width: '100%' }}
            notMerge
            lazyUpdate
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            ROI 收益分布（-50%~50%，每 10% 档位投资次数）
          </Typography>
          <ReactECharts
            option={buildRoiBucketOption(metrics)}
            style={{ height: 190, width: '100%' }}
            notMerge
            lazyUpdate
          />
        </Box>
      </SectionBlock>

      <StockKlineDialog
        open={Boolean(selectedStock)}
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
      />
    </Stack>
  );
}

export default PriceFactorReport;
