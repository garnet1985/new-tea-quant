import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import { buildPriceSampleStockRows } from '../../../mocks/strategyReportSampleRows';
import { REPORT_BLOCK_UNAVAILABLE_ZH } from '../../../mocks/strategyReportMetrics';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';

const EMPTY_METRICS_BASE = {
  totalInvestments: 0,
  winRate: 0,
  avgRoi: 0,
  avgDurationDays: 0,
};

function UnavailableHint() {
  return (
    <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
      {REPORT_BLOCK_UNAVAILABLE_ZH}
    </Typography>
  );
}

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

function PriceFactorReport({
  metrics,
  stockRows,
  strategyName: _strategyName,
  runId: _runId,
  title = '价格回测报告',
  showStockGrid = true,
}) {
  const [stockSearch, setStockSearch] = useState('');

  const avail = metrics?._availability ?? {
    overview: false,
    sampleCoverage: false,
    profitBasics: false,
    roiPercentileViz: false,
    roiBucketViz: false,
  };

  const derivedStockRows = useMemo(() => {
    if (Array.isArray(stockRows) && stockRows.length > 0) return stockRows;
    const base = metrics || EMPTY_METRICS_BASE;
    return buildPriceSampleStockRows(base);
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

  const stockColumns = useMemo(() => [
    { field: 'stockCode', headerName: '代码', flex: 1, minWidth: 120 },
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

  if (!metrics || typeof metrics !== 'object') {
    return <UnavailableHint />;
  }

  const percentileHint = avail.roiPercentileViz
    ? [
      Number.isFinite(metrics.roiIqr) ? `IQR ${metrics.roiIqr}%` : '',
      metrics.roiConclusion || '',
    ].filter(Boolean).join(' · ')
    : '';

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      <Typography variant="caption" color="text.secondary">
        K 线与买卖点透视暂未启用（需加载行情并描点后再接）。
      </Typography>

      {showStockGrid ? (
        <ReportStockSampleGrid
          title="逐股样本"
          tip="用于查看本次价格回测中单股表现；支持搜索、表头排序与底部分页。（逐股接口接入后将替换占位样本）"
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          rows={filteredRows}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="回测总体"
        tip="用于判断信号层是否具备正向收益，且收益效率是否可接受。"
      >
        {avail.overview ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard title="胜率" value={`${metrics.winRate}%`} />
            <MetricCard title="平均每笔 ROI" value={`${metrics.avgRoi}%`} />
            <MetricCard title="平均持有时长" value={`${metrics.avgDurationDays} 天`} />
            <MetricCard title="年化收益（自然日）" value={`${metrics.annualReturn}%`} />
          </Box>
        ) : <UnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="样本与覆盖"
        tip="用于确认结果是否来自足够样本，避免小样本导致结论失真。"
      >
        {avail.sampleCoverage ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard title="总投资次数" value={metrics.totalInvestments.toLocaleString()} />
            <MetricCard title="产生机会股票数" value={metrics.stocksWithOpportunities.toLocaleString()} />
            <MetricCard title="每股平均投资次数" value={metrics.avgInvestmentsPerStock.toFixed(2)} />
            <MetricCard title="未完成持仓数" value={metrics.totalOpenInvestments.toLocaleString()} />
          </Box>
        ) : <UnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="盈亏结构（含 ROI 分位）"
        tip="用于观察收益分布是否健康，避免只靠少数大盈利机会拉高均值。"
      >
        {avail.profitBasics ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="盈亏次数"
              value={`${metrics.totalWinInvestments} / ${metrics.totalLossInvestments}`}
              hint="赢单 / 亏单"
            />
            <MetricCard title="每笔平均盈利" value={metrics.avgProfitPerInvestment.toLocaleString()} />
            <MetricCard title="每股平均盈利" value={metrics.avgProfitPerStock.toLocaleString()} />
          </Box>
        ) : <UnavailableHint />}
        {avail.profitBasics && avail.roiPercentileViz ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1, mt: 1 }}>
            <MetricCard
              title="ROI 分位摘要"
              value={`P25 ${metrics.roiP25}% · P50 ${metrics.roiP50}% · P75 ${metrics.roiP75}%`}
              hint={percentileHint}
            />
          </Box>
        ) : null}
        {!avail.roiPercentileViz ? (
          <Box sx={{ mt: avail.profitBasics ? 1 : 0 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              ROI 分位图（依赖后端写入 roiPercentileValues 等字段；当前 PriceReport 未产出）
            </Typography>
            <UnavailableHint />
          </Box>
        ) : (
          <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              ROI 分位图（10% / 20% / … / 90%）
            </Typography>
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
              ROI 桶分布（依赖后端写入 roiBucketLabels / roiBucketCounts）
            </Typography>
            <UnavailableHint />
          </Box>
        ) : (
          <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              ROI 收益分布（档位投资次数）
            </Typography>
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
