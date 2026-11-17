import React, { useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Button, Dialog } from 'ui';
import ReportStockSampleGrid from '../reportStockSampleGrid';
import ReportBlock from 'ntq-ui/reportBlock';
import { resolveMarketPnlPalette } from 'styles/marketPnlColors';
import { CAPITAL_CHART_TIPS } from '../reportMetricTips';
import ReportUnavailableHint from '../reportUnavailableHint';
import { formatReportMoney } from '../lib/formatReportMoney';
import { formatReportChartDateLabel } from '../lib/reportDateFormat';
import {
  buildPortfolioTradeOverviewChartOption,
  buildTradeLifecycleTableRows,
} from '../lib/portfolioTradeLifecycle';
import './style.scss';

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
    <Button
      variant="glass"
      icon="monitoring"
      disabled={disabled}
      aria-label="打开逐笔事件图"
      tooltip="打开逐笔事件图"
      className="ntq-report-trade-chart-btn"
      onClick={onClick}
    />
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
          return <span className="ntq-report-trade-cell">{name || code}</span>;
        }
        return (
          <span className="ntq-report-trade-cell ntq-report-trade-cell--pair">
            <span className="ntq-report-trade-cell__name">{name}</span>
            <span className="ntq-report-trade-cell__code ntq-muted">{code}</span>
          </span>
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
          return <span className="ntq-report-trade-cell ntq-muted">未平仓</span>;
        }
        return (
          <span className="ntq-report-trade-cell">
            {formatReportChartDateLabel(params.row.endDate)}
          </span>
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
          return <span className="ntq-report-trade-cell ntq-muted">—</span>;
        }
        return <span className="ntq-report-trade-cell">{`${days}天`}</span>;
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
          <span className="ntq-report-trade-cell">
            {costText}
            <span className="ntq-muted">{` （${shareText}）`}</span>
          </span>
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
          return <span className="ntq-report-trade-cell ntq-muted">未平仓</span>;
        }
        const pct = Number(params.row.returnPct);
        if (!Number.isFinite(pct)) {
          return <span className="ntq-report-trade-cell ntq-muted">—</span>;
        }
        const color = outcomeColor(params.row, palette);
        return (
          <span className="ntq-report-trade-cell ntq-report-trade-cell--emph" style={{ color }}>
            {`${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`}
          </span>
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
          return <span className="ntq-report-trade-cell ntq-muted">未平仓</span>;
        }
        const profit = Number(params.row.profit);
        if (!Number.isFinite(profit)) {
          return <span className="ntq-report-trade-cell ntq-muted">—</span>;
        }
        const color = outcomeColor(params.row, palette);
        return (
          <span className="ntq-report-trade-cell ntq-report-trade-cell--emph" style={{ color }}>
            {`${profit >= 0 ? '+' : ''}${formatReportMoney(profit)}`}
          </span>
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
      title={(
        <span className="ntq-report-dialog-title">
          <span className="ntq-report-dialog-title__main">
            逐笔投资事件图
            <span className="ntq-report-dialog-title__sub ntq-muted">
              净值曲线 · 仅标开仓起点（同日合并 · 赚红亏绿 · 按金额分三档大小）
            </span>
          </span>
          <Button
            variant="ghost"
            icon="close"
            aria-label="关闭"
            onClick={() => setChartOpen(false)}
          />
        </span>
      )}
    >
      <p className="ntq-caption ntq-muted">
        与表格同源。同日多笔开仓合并为一点：总盈亏金额为正红、为负绿；点大小按 |金额| 分小/中/大。
        悬停看当日明细。底部滑条缩放。
      </p>
      {overviewOption ? (
        <ReactECharts
          option={overviewOption}
          style={{ height: 'min(72vh, 640px)', width: '100%' }}
          notMerge
          lazyUpdate
        />
      ) : (
        <p className="ntq-muted">暂无曲线或成交数据，无法绘制事件图。</p>
      )}
    </Dialog>
  ) : null;

  if (!rows.length) {
    return (
      <>
        <ReportBlock
          title="逐笔投资"
          tip={CAPITAL_CHART_TIPS.tradeLifecycle}
          action={chartAction}
        >
          <div className="ntq-report-trade-empty">
            <ReportUnavailableHint message="暂无成交记录" />
          </div>
        </ReportBlock>
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
