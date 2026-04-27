import React, { useMemo, useState } from 'react';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
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

const STOCK_NAME_POOL = [
  '贵州茅台',
  '五粮液',
  '中国平安',
  '招商银行',
  '美的集团',
  '比亚迪',
  '隆基绿能',
  '宁德时代',
  '中芯国际',
  '海康威视',
  '恒瑞医药',
  '中国中免',
  '紫金矿业',
  '迈瑞医疗',
  '中信证券',
];

const STOCK_CODE_POOL = [
  '600519.SH',
  '000858.SZ',
  '601318.SH',
  '600036.SH',
  '000333.SZ',
  '002594.SZ',
  '601012.SH',
  '300750.SZ',
  '688981.SH',
  '002415.SZ',
  '600276.SH',
  '601888.SH',
  '601899.SH',
  '300760.SZ',
  '600030.SH',
];

function buildEnumSampleStocks(metrics) {
  const count = Math.max(10, Math.min(15, metrics.triggerStocks || 10));
  const avgBase = Number(metrics.avgPerStock || 0);
  return Array.from({ length: count }).map((_, index) => {
    const seed = index + 1;
    const opportunities = Math.max(1, Math.round(avgBase * (0.6 + (seed % 7) * 0.22)));
    const completionRate = Math.max(35, Math.min(98, Number((metrics.completedRatio + (seed % 5) * 2.2 - 5.5).toFixed(1))));
    const triggerSpanDays = Math.max(3, Math.round(metrics.meanGap + (seed % 6) * 1.8));
    return {
      id: `${STOCK_CODE_POOL[index] || `688${900 + seed}.SH`}-${seed}`,
      stockCode: STOCK_CODE_POOL[index] || `688${900 + seed}.SH`,
      stockName: STOCK_NAME_POOL[index] || `样本股票${seed}`,
      opportunities,
      completionRate,
      triggerSpanDays,
    };
  });
}

function OpportunityEnumrateReport({ metrics, title = '枚举核心结论（草图）', showStockGrid = true }) {
  const [stockSearch, setStockSearch] = useState('');
  const [stockSortBy, setStockSortBy] = useState('default');

  const stockRows = useMemo(() => buildEnumSampleStocks(metrics || {}), [metrics]);

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
        <SectionBlock
          title="样本股票（最多 10 只）"
          tip="用于快速查看枚举阶段的单股机会覆盖情况，支持搜索和核心参数排序。"
        >
          <Stack spacing={1}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
              <TextField
                size="small"
                placeholder="搜索代码或名称..."
                value={stockSearch}
                onChange={(event) => setStockSearch(event.target.value)}
                sx={{ minWidth: { xs: '100%', md: 220 } }}
              />
              <FormControl size="small" sx={{ minWidth: { xs: '100%', md: 200 } }}>
                <InputLabel id="enum-stock-sort-label">排序</InputLabel>
                <Select
                  labelId="enum-stock-sort-label"
                  value={stockSortBy}
                  label="排序"
                  onChange={(event) => setStockSortBy(event.target.value)}
                >
                  <MenuItem value="default">接口顺序</MenuItem>
                  <MenuItem value="opportunitiesDesc">机会数（高到低）</MenuItem>
                  <MenuItem value="completionDesc">完整度（高到低）</MenuItem>
                  <MenuItem value="spanAsc">平均机会间隔（低到高）</MenuItem>
                </Select>
              </FormControl>
            </Stack>
            <Box sx={{ height: 360 }}>
              <DataGrid
                rows={filteredAndSortedRows}
                columns={stockColumns}
                hideFooter
                disableColumnMenu
                disableColumnFilter
                disableRowSelectionOnClick
                density="compact"
              />
            </Box>
          </Stack>
        </SectionBlock>
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
