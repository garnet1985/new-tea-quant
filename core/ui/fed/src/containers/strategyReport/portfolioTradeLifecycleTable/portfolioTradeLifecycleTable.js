import React, { useMemo, useState } from 'react';
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Typography,
} from '@mui/material';
import ReactECharts from 'echarts-for-react';
import NtqIcon from 'views/ntqIcon';
import ReportStockSampleGrid from 'views/reportStockSampleGrid';
import { SectionBlock } from 'views/sectionBlock';
import { resolveMarketPnlPalette } from 'styles/marketPnlColors';
import { CAPITAL_CHART_TIPS } from '../reportMetricTips';
import ReportUnavailableHint from '../reportUnavailableHint';
import { formatReportMoney } from '../lib/formatReportMoney';
import { formatReportChartDateLabel } from '../lib/reportDateFormat';
import {
  buildPortfolioTradeOverviewChartOption,
  buildTradeLifecycleTableRows,
} from '../lib/portfolioTradeLifecycle';

function outcomeColor(row, palette) {
  if (row.open) return undefined;
  return row.outcome === 'loss' ? palette.loss : palette.profit;
}

function emptyLastComparator(a, b) {
  const aEmpty = a == null || a === '';
  const bEmpty = b == null || b === '';
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b));
}

function TradeChartOpenButton({ onClick, disabled = false }) {
  return (
    <IconButton
      size="small"
      disabled={disabled}
      aria-label="打开逐笔事件图"
      title="打开逐笔事件图"
      onClick={onClick}
      sx={{
        border: '1px solid',
        borderColor: disabled ? 'rgba(255,255,255,0.18)' : 'rgba(255,255,255,0.42)',
        borderRadius: 1,
        px: 0.75,
        py: 0.5,
        bgcolor: disabled ? 'transparent' : 'rgba(255,255,255,0.04)',
        '&:hover': disabled ? undefined : {
          borderColor: 'rgba(255,255,255,0.72)',
          bgcolor: 'rgba(255,255,255,0.10)',
        },
      }}
    >
      <NtqIcon name="monitoring" size={18} tone={disabled ? 'muted' : ''} />
    </IconButton>
  );
}

/**
 * 逐笔投资表；主报告可打开整表事件图（对比窗不显示入口）。
 */
function PortfolioTradeLifecycleTable({ metrics, showChartAction = true }) {
  const [search, setSearch] = useState('');
  const [chartOpen, setChartOpen] = useState(false);

  const palette = useMemo(
    () => resolveMarketPnlPalette(metrics?.marketProfile || metrics?.market_profile),
    [metrics],
  );

  const rows = useMemo(
    () => buildTradeLifecycleTableRows(metrics?.tradeEvents),
    [metrics?.tradeEvents],
  );

  const filteredRows = useMemo(() => {
    const q = String(search || '').trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => {
      const name = String(row.stockName || '').toLowerCase();
      const code = String(row.entityId || '').toLowerCase();
      return name.includes(q) || code.includes(q);
    });
  }, [rows, search]);

  const overviewOption = useMemo(() => {
    if (!chartOpen || !metrics) return null;
    return buildPortfolioTradeOverviewChartOption(metrics);
  }, [chartOpen, metrics]);

  const columns = useMemo(() => [
    {
      field: 'stock',
      headerName: '股票',
      width: 168,
      valueGetter: (params) => {
        const name = params.row.stockName || '';
        const code = params.row.entityId || '';
        return name && code && name !== code ? `${name} ${code}` : (name || code);
      },
      renderCell: (params) => {
        const name = params.row.stockName || '';
        const code = params.row.entityId || '';
        if (!name && !code) return '—';
        if (!code || code === name) {
          return <Typography variant="body2" noWrap>{name || code}</Typography>;
        }
        return (
          <Stack direction="row" spacing={0.75} alignItems="baseline" sx={{ minWidth: 0 }}>
            <Typography variant="body2" noWrap>
              {name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {code}
            </Typography>
          </Stack>
        );
      },
    },
    {
      field: 'startDate',
      headerName: '买入时间',
      width: 112,
      valueFormatter: (params) => formatReportChartDateLabel(params.value) || '—',
    },
    {
      field: 'endDate',
      headerName: '卖出时间',
      width: 112,
      valueGetter: (params) => params.row.endDate || '',
      sortComparator: emptyLastComparator,
      renderCell: (params) => {
        if (params.row.open || !params.row.endDate) {
          return <Typography variant="body2" color="text.secondary">未平仓</Typography>;
        }
        return (
          <Typography variant="body2">
            {formatReportChartDateLabel(params.row.endDate)}
          </Typography>
        );
      },
    },
    {
      field: 'holdingDays',
      headerName: '持有天数',
      width: 96,
      sortComparator: emptyLastComparator,
      renderCell: (params) => {
        const days = params.row.holdingDays;
        if (!Number.isFinite(Number(days))) {
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        return <Typography variant="body2">{`${days}天`}</Typography>;
      },
    },
    {
      field: 'cost',
      headerName: '投资',
      width: 148,
      valueGetter: (params) => {
        const n = Number(params.row.cost);
        return Number.isFinite(n) ? n : null;
      },
      sortComparator: emptyLastComparator,
      renderCell: (params) => {
        const shares = Number(params.row.shares);
        const cost = params.row.cost;
        const costText = Number.isFinite(Number(cost)) ? formatReportMoney(cost) : '—';
        const shareText = Number.isFinite(shares) ? `${shares.toLocaleString()}股` : '—股';
        return (
          <Typography variant="body2" noWrap>
            {costText}
            <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
              （{shareText}）
            </Typography>
          </Typography>
        );
      },
    },
    {
      field: 'buyPrice',
      headerName: '买入价',
      width: 92,
      valueFormatter: (params) => (
        Number.isFinite(Number(params.value)) ? formatReportMoney(params.value) : '—'
      ),
    },
    {
      field: 'returnPct',
      headerName: 'ROI',
      width: 96,
      sortComparator: emptyLastComparator,
      renderCell: (params) => {
        if (params.row.open) {
          return <Typography variant="body2" color="text.secondary">未平仓</Typography>;
        }
        const pct = Number(params.row.returnPct);
        if (!Number.isFinite(pct)) {
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        const color = outcomeColor(params.row, palette);
        return (
          <Typography variant="body2" sx={{ color, fontWeight: 600 }}>
            {`${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`}
          </Typography>
        );
      },
    },
    {
      field: 'profit',
      headerName: '盈亏',
      width: 112,
      sortComparator: emptyLastComparator,
      renderCell: (params) => {
        if (params.row.open) {
          return <Typography variant="body2" color="text.secondary">未平仓</Typography>;
        }
        const profit = Number(params.row.profit);
        if (!Number.isFinite(profit)) {
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        const color = outcomeColor(params.row, palette);
        return (
          <Typography variant="body2" sx={{ color, fontWeight: 600 }}>
            {`${profit >= 0 ? '+' : ''}${formatReportMoney(profit)}`}
          </Typography>
        );
      },
    },
  ], [palette]);

  const chartAction = showChartAction
    ? (
      <TradeChartOpenButton
        disabled={!rows.length}
        onClick={() => setChartOpen(true)}
      />
    )
    : null;

  const chartDialog = showChartAction ? (
    <Dialog
      open={chartOpen}
      onClose={() => setChartOpen(false)}
      fullScreen
      className="ntq-report-trade-overview-dialog"
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
          py: 1.25,
          pr: 1,
        }}
      >
        <Typography variant="subtitle1" fontWeight={700} component="span">
          逐笔投资事件图
          <Typography
            component="span"
            variant="caption"
            color="text.secondary"
            sx={{ ml: 1.5 }}
          >
            净值曲线 · 仅标开仓起点（同日合并 · 赚红亏绿 · 按金额分三档大小）
          </Typography>
        </Typography>
        <IconButton aria-label="关闭" onClick={() => setChartOpen(false)} edge="end">
          <NtqIcon name="cancel" size={18} />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ display: 'flex', flexDirection: 'column', gap: 1, pt: 1.5 }}>
        <Typography variant="caption" color="text.secondary">
          与表格同源。同日多笔开仓合并为一点：总盈亏金额为正红、为负绿；点大小按 |金额| 分小/中/大。
          悬停看当日明细。底部滑条缩放。
        </Typography>
        {overviewOption ? (
          <ReactECharts
            option={overviewOption}
            style={{ height: 'min(72vh, 640px)', width: '100%' }}
            notMerge
            lazyUpdate
          />
        ) : (
          <Typography variant="body2" color="text.secondary">
            暂无曲线或成交数据，无法绘制事件图。
          </Typography>
        )}
      </DialogContent>
    </Dialog>
  ) : null;

  if (!rows.length) {
    return (
      <>
        <SectionBlock
          title="逐笔投资"
          tip={CAPITAL_CHART_TIPS.tradeLifecycle}
          action={chartAction}
        >
          <Box sx={{ py: 0.5 }}>
            <ReportUnavailableHint message="暂无成交记录" />
          </Box>
        </SectionBlock>
        {chartDialog}
      </>
    );
  }

  return (
    <>
      <ReportStockSampleGrid
        title="逐笔投资"
        tip={CAPITAL_CHART_TIPS.tradeLifecycle}
        headerAction={chartAction}
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="搜索代码或名称..."
        rows={filteredRows}
        columns={columns}
        gridHeight={360}
        defaultPageSize={10}
        initialSortModel={[{ field: 'startDate', sort: 'desc' }]}
      />
      {chartDialog}
    </>
  );
}

export default PortfolioTradeLifecycleTable;
