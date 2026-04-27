import React from 'react';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import {
  Box,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import ReactECharts from 'echarts-for-react';

function MetricCard({ title, value, hint }) {
  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        p: 1.25,
        backgroundColor: 'background.paper',
      }}
    >
      <Stack spacing={0.25}>
        <Typography variant="caption" color="text.secondary">{title}</Typography>
        <Typography variant="h6" fontWeight={700} lineHeight={1.2}>{value}</Typography>
        {hint ? <Typography variant="caption" color="text.secondary">{hint}</Typography> : null}
      </Stack>
    </Box>
  );
}

function SectionTitle({ title, tip }) {
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <Typography variant="subtitle2" fontWeight={700}>{title}</Typography>
      <Tooltip title={tip} placement="top">
        <InfoOutlinedIcon sx={{ fontSize: 15, color: 'text.secondary' }} />
      </Tooltip>
    </Stack>
  );
}

function SectionBlock({ title, tip, children }) {
  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        p: 1.25,
        backgroundColor: 'background.paper',
      }}
    >
      <Stack spacing={1}>
        <SectionTitle title={title} tip={tip} />
        {children}
      </Stack>
    </Box>
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

function PriceFactorReport({ metrics, title = '价格回测报告（草图）' }) {
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
    </Stack>
  );
}

export default PriceFactorReport;
