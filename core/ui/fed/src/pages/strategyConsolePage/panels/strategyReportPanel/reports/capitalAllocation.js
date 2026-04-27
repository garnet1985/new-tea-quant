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

function buildCapitalSampleStocks(metrics) {
  const count = Math.max(10, Math.min(15, metrics.stockCount || 10));
  const avgPnl = Number(metrics.avgPnlPerTrade || 0);
  const avgTradesPerStock = Number(metrics.avgTradesPerStock || 1);
  return Array.from({ length: count }).map((_, index) => {
    const seed = index + 1;
    const tradeCount = Math.max(1, Math.round(avgTradesPerStock + (seed % 6) * 0.8));
    const pnl = Math.round(avgPnl * tradeCount * (0.7 + (seed % 7) * 0.18) - ((seed % 4) * 1200));
    const winRate = Math.max(20, Math.min(92, Number((metrics.winRatePct + (seed % 5) * 3 - 6).toFixed(1))));
    return {
      id: `${STOCK_CODE_POOL[index] || `688${910 + seed}.SH`}-${seed}`,
      stockCode: STOCK_CODE_POOL[index] || `688${910 + seed}.SH`,
      stockName: STOCK_NAME_POOL[index] || `样本股票${seed}`,
      tradeCount,
      pnl,
      winRate,
    };
  });
}

function CapitalAllocationReport({ metrics, title = '资金模拟报告（草图）', showStockGrid = true }) {
  const [stockSearch, setStockSearch] = useState('');
  const [stockSortBy, setStockSortBy] = useState('default');

  const stockRows = useMemo(() => buildCapitalSampleStocks(metrics || {}), [metrics]);

  const filteredAndSortedRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    const filtered = keyword
      ? stockRows.filter((row) => (
        row.stockCode.toLowerCase().includes(keyword) || row.stockName.toLowerCase().includes(keyword)
      ))
      : stockRows;
    const sorted = [...filtered];
    if (stockSortBy === 'pnlDesc') sorted.sort((a, b) => b.pnl - a.pnl);
    if (stockSortBy === 'tradeCountDesc') sorted.sort((a, b) => b.tradeCount - a.tradeCount);
    if (stockSortBy === 'winRateDesc') sorted.sort((a, b) => b.winRate - a.winRate);
    return sorted.slice(0, 10);
  }, [stockRows, stockSearch, stockSortBy]);

  const stockColumns = [
    { field: 'stockCode', headerName: '代码', flex: 1, minWidth: 120 },
    { field: 'stockName', headerName: '名称', flex: 1, minWidth: 120 },
    {
      field: 'tradeCount',
      headerName: '交易次数',
      width: 110,
      valueFormatter: (params) => `${params.value} 次`,
    },
    {
      field: 'pnl',
      headerName: '累计盈亏',
      width: 130,
      valueFormatter: (params) => `${params.value >= 0 ? '+' : ''}${Number(params.value).toLocaleString()}`,
    },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
  ];

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      {showStockGrid ? (
        <SectionBlock
          title="样本股票（最多 10 只）"
          tip="用于快速查看资金模拟阶段的单股交易结果，支持搜索和核心参数排序。"
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
                <InputLabel id="capital-stock-sort-label">排序</InputLabel>
                <Select
                  labelId="capital-stock-sort-label"
                  value={stockSortBy}
                  label="排序"
                  onChange={(event) => setStockSortBy(event.target.value)}
                >
                  <MenuItem value="default">接口顺序</MenuItem>
                  <MenuItem value="pnlDesc">累计盈亏（高到低）</MenuItem>
                  <MenuItem value="tradeCountDesc">交易次数（高到低）</MenuItem>
                  <MenuItem value="winRateDesc">胜率（高到低）</MenuItem>
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
