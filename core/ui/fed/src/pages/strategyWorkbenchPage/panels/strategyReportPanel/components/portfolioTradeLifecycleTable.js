import React, { useMemo, useState } from 'react';
import { Box, IconButton, Stack, Typography } from '@mui/material';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import { resolveMarketPnlPalette } from 'theme/marketPnlColors';
import { CAPITAL_CHART_TIPS } from '../reportMetricTips';
import ReportUnavailableHint from './reportUnavailableHint';
import { formatReportMoney } from '../lib/formatReportMoney';
import { formatReportChartDateLabel } from '../lib/reportDateFormat';
import { buildTradeLifecycleTableRows } from '../lib/portfolioTradeLifecycle';

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

function ChartPlaceholderButton() {
  return (
    <IconButton
      size="small"
      disabled
      aria-label="逐笔事件图（即将提供）"
      title="整表事件图即将提供"
    >
      <NtqIcon name="monitoring" size={18} tone="muted" />
    </IconButton>
  );
}

/**
 * 逐笔投资表：数据来自 capitalMetrics.tradeEvents（trades.json）。
 * 整表事件图入口为标题栏右侧占位（尚未实施）。
 */
function PortfolioTradeLifecycleTable({ metrics }) {
  const [search, setSearch] = useState('');

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

  if (!rows.length) {
    return (
      <SectionBlock
        title="逐笔投资"
        tip={CAPITAL_CHART_TIPS.tradeLifecycle}
        action={<ChartPlaceholderButton />}
      >
        <Box sx={{ py: 0.5 }}>
          <ReportUnavailableHint message="暂无成交记录" />
        </Box>
      </SectionBlock>
    );
  }

  return (
    <ReportStockSampleGrid
      title="逐笔投资"
      tip={CAPITAL_CHART_TIPS.tradeLifecycle}
      headerAction={<ChartPlaceholderButton />}
      searchValue={search}
      onSearchChange={setSearch}
      searchPlaceholder="搜索代码或名称..."
      rows={filteredRows}
      columns={columns}
      gridHeight={360}
      defaultPageSize={10}
      initialSortModel={[{ field: 'startDate', sort: 'desc' }]}
    />
  );
}

export default PortfolioTradeLifecycleTable;
