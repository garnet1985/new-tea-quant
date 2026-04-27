import React, { useMemo, useState } from 'react';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
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
  '药明康德',
  '万华化学',
  '立讯精密',
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
  '603259.SH',
  '600309.SH',
  '002475.SZ',
];

function buildSampleStocks(metrics) {
  const baseCount = Math.max(10, Math.min(18, metrics.totalInvestments));
  return Array.from({ length: baseCount }).map((_, index) => {
    const seed = index + 1;
    const winRate = Math.max(20, Math.min(92, Number((metrics.winRate + (seed % 5) * 4 - 8).toFixed(1))));
    const roi = Number((metrics.avgRoi + (seed % 7) * 2.3 - 6.9).toFixed(1));
    const holdDays = Math.max(3, Math.round(metrics.avgDurationDays + (seed % 6) * 3 - 7));
    return {
      id: `${STOCK_CODE_POOL[index]}-${seed}`,
      stockCode: STOCK_CODE_POOL[index] || `688${900 + seed}.SH`,
      stockName: STOCK_NAME_POOL[index] || `样本股票${seed}`,
      winRate,
      roi,
      holdDays,
    };
  });
}

function hashString(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = ((hash << 5) - hash) + text.charCodeAt(i);
  return Math.abs(hash);
}

function buildStockKlineOption(stock) {
  if (!stock) return {};
  const seed = hashString(stock.stockCode);
  const points = 42;
  const dates = Array.from({ length: points }).map((_, index) => `D${index + 1}`);
  const base = 80 + (seed % 120);
  let prevClose = base;
  const candleData = dates.map((_, index) => {
    const drift = Math.sin((index + (seed % 7)) / 4.5) * 1.7 + ((seed + index) % 5 - 2) * 0.35;
    const open = Number((prevClose + drift * 0.4).toFixed(2));
    const close = Number((open + drift).toFixed(2));
    const high = Number((Math.max(open, close) + 0.8 + ((seed + index) % 3) * 0.35).toFixed(2));
    const low = Number((Math.min(open, close) - 0.8 - ((seed + index) % 2) * 0.4).toFixed(2));
    prevClose = close;
    return [open, close, low, high];
  });
  const buyIndex = 9;
  const sellIndex = 31;
  const buyPrice = candleData[buyIndex]?.[1];
  const sellPrice = candleData[sellIndex]?.[1];

  return {
    animation: false,
    grid: { left: 36, right: 12, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: dates,
      scale: true,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 10 },
    },
    yAxis: {
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 10 },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    series: [
      {
        type: 'candlestick',
        data: candleData,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      {
        type: 'scatter',
        symbolSize: 10,
        data: [
          { value: [buyIndex, buyPrice], itemStyle: { color: '#2E7D32' }, label: { show: true, formatter: '买入', position: 'top' } },
          { value: [sellIndex, sellPrice], itemStyle: { color: '#C62828' }, label: { show: true, formatter: '卖出', position: 'top' } },
        ],
        tooltip: {
          formatter: (params) => `${params.data?.label?.formatter || '点位'}：${params.value?.[1] || '--'}`,
        },
      },
    ],
  };
}

function PriceFactorReport({ metrics, title = '价格回测报告（草图）', showStockGrid = true }) {
  const [stockSearch, setStockSearch] = useState('');
  const [stockSortBy, setStockSortBy] = useState('default');
  const [selectedStock, setSelectedStock] = useState(null);
  const stockRows = useMemo(() => {
    const base = metrics || {
      totalInvestments: 0,
      winRate: 0,
      avgRoi: 0,
      avgDurationDays: 0,
    };
    return buildSampleStocks(base);
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

  const stockColumns = [
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
  ];

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
        <SectionBlock
          title="样本股票（最多 10 只）"
          tip="用于快速查看本次价格回测中代表性股票的核心表现，支持搜索和核心参数排序。点击代码可查看 K 线与买卖点。"
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
              <FormControl size="small" sx={{ minWidth: { xs: '100%', md: 180 } }}>
                <InputLabel id="price-stock-sort-label">排序</InputLabel>
                <Select
                  labelId="price-stock-sort-label"
                  value={stockSortBy}
                  label="排序"
                  onChange={(event) => setStockSortBy(event.target.value)}
                >
                  <MenuItem value="default">接口顺序</MenuItem>
                  <MenuItem value="winRateDesc">胜率（高到低）</MenuItem>
                  <MenuItem value="roiDesc">ROI（高到低）</MenuItem>
                  <MenuItem value="holdDaysAsc">平均投资天数（低到高）</MenuItem>
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

      <Dialog open={Boolean(selectedStock)} onClose={() => setSelectedStock(null)} maxWidth="lg" fullWidth>
        <DialogTitle>
          {selectedStock ? `${selectedStock.stockCode} · ${selectedStock.stockName}` : 'K 线详情'}
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            展示该股票区间 K 线，以及本次回测中的买入/卖出点位（当前为 mock 示意）。
          </Typography>
          <ReactECharts
            option={buildStockKlineOption(selectedStock)}
            style={{ height: 420, width: '100%' }}
            notMerge
            lazyUpdate
          />
        </DialogContent>
      </Dialog>
    </Stack>
  );
}

export default PriceFactorReport;
