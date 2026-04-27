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

function OpportunityEnumrateReport({ metrics, title = '枚举核心结论（草图）' }) {
  if (!metrics) {
    return (
      <Typography variant="body2" color="text.secondary">
        暂无枚举结果。
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

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
