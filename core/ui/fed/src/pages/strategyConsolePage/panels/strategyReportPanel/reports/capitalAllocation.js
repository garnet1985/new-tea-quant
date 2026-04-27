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

function buildEquityCurveOption(metrics) {
  return {
    animation: false,
    grid: { left: 36, right: 10, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: metrics.equityCurveLabels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 4,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#5F6368',
        fontSize: 11,
        formatter: (value) => `${(value / 10000).toFixed(0)}w`,
      },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
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
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>总资产：${Number(point.data).toLocaleString()}`;
      },
    },
  };
}

function buildDrawdownCurveOption(metrics) {
  return {
    animation: false,
    grid: { left: 36, right: 10, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: metrics.equityCurveLabels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
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
      trigger: 'axis',
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>回撤：${point.data}%`;
      },
    },
  };
}

function CapitalAllocationReport({ metrics, title = '资金模拟报告（草图）' }) {
  if (!metrics) {
    return (
      <Typography variant="body2" color="text.secondary">
        暂无资金模拟结果。
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      <SectionBlock
        title="资金结果总览"
        tip="先看赚了多少、承受了多大回撤，并结合资产曲线判断收益路径是否平滑。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="初始资金" value={metrics.initialCapital.toLocaleString()} />
          <MetricCard title="最终总资产" value={metrics.finalEquity.toLocaleString()} />
          <MetricCard title="总收益率" value={`${metrics.totalReturnPct}%`} />
          <MetricCard title="收益回撤比（Calmar）" value={metrics.calmarRatio} />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            资产曲线（总资产随时间变化）
          </Typography>
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
        tip="用于判断收益是否来自稳定交易，而不是少数极端收益单。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="总交易次数" value={metrics.totalTrades.toLocaleString()} hint={`买入 ${metrics.buyTrades} / 卖出 ${metrics.sellTrades}`} />
          <MetricCard title="胜率" value={`${metrics.winRatePct}%`} hint={`盈利 ${metrics.winTrades} / 亏损 ${metrics.lossTrades}`} />
          <MetricCard title="总盈亏金额" value={metrics.totalProfit.toLocaleString()} />
          <MetricCard title="单笔平均盈亏" value={metrics.avgPnlPerTrade.toLocaleString()} />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="仓位与资金利用率"
        tip="用于观察资金是否有效投入市场，以及是否长期处于空仓或满仓。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="平均持仓数" value={`${metrics.avgOpenPositions} / ${metrics.peakPositions}`} />
          <MetricCard title="满仓天数占比" value={`${metrics.fullExposureDaysRatio}%`} />
          <MetricCard title="平均现金占比" value={`${metrics.avgCashRatio}%`} />
          <MetricCard title="资金利用率" value={`${metrics.capitalUtilizationRatio}%`} />
        </Box>
      </SectionBlock>

      <SectionBlock
        title="风险结构"
        tip="用于识别最坏情境：连续亏损、回撤持续和尾部亏损规模。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="最大回撤" value={`${metrics.maxDrawdownPct}%`} />
          <MetricCard title="最大回撤持续天数" value={`${metrics.maxDrawdownDurationDays} 天`} />
          <MetricCard title="最长连续亏损" value={`${metrics.maxLossStreak} 笔`} />
          <MetricCard
            title="Top3 单笔亏损"
            value={metrics.worstTradePnls.map((value) => value.toLocaleString()).join(' / ')}
          />
        </Box>
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            回撤曲线（资产曲线对应的回撤深度）
          </Typography>
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
        tip="用于评估收益是否过度依赖少数股票，降低回测结果偶然性。"
      >
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
          <MetricCard title="触发股票数" value={metrics.stockCount.toLocaleString()} />
          <MetricCard title="每股平均交易次数" value={metrics.avgTradesPerStock.toFixed(2)} />
          <MetricCard title="前 5 股票收益贡献占比" value={`${metrics.top5ContributionRatio}%`} />
          <MetricCard title="股票收益离散系数（CV）" value={metrics.stockPnlCv} />
        </Box>
      </SectionBlock>
    </Stack>
  );
}

export default CapitalAllocationReport;
