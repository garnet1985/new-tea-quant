import React from 'react';
import { Button, DefinitionList, Dialog, Tag } from 'ui';
import { formatMoney } from './decisionFormat';
import {
  StockStatusChips,
  formatHoldingPnl,
  formatMarketValueWithPnl,
  holdingStockLabel,
} from './decisionPlayHelpers';

export function formatHoldSpan(days, unit) {
  const n = Number(days) || 0;
  if (unit === 'trading_day') return `${n} 个交易日`;
  if (unit === 'open_day') return `${n} 个开市日`;
  return `${n} 个自然日`;
}

export function HoldingDetailDialog({
  row,
  open,
  equity,
  onClose,
  onOpenKline,
  statusTags = [],
  statusLoading = false,
}) {
  const weight = row?.marketValue != null
    && Number.isFinite(Number(row.marketValue))
    && Number.isFinite(Number(equity))
    && Number(equity) > 0
    ? Number(row.marketValue) / Number(equity)
    : null;
  const kv = row ? [
    ['股票', (
      <span className="decision-stock-with-status">
        {holdingStockLabel(row)}
        <StockStatusChips tags={statusTags} loading={statusLoading} />
      </span>
    )],
    ['持有', `${Number(row.shares).toLocaleString()} 股`],
    ['买入日', row.buyDate || '—'],
    ['买入价', row.buyPrice != null ? formatMoney(row.buyPrice) : '—'],
    ['现价', row.close != null ? formatMoney(row.close) : '—'],
    ['总成本', row.cost != null ? formatMoney(row.cost) : '—'],
    ['总价值', formatMarketValueWithPnl(row.marketValue, row.unrealized)],
    ['浮动盈亏', formatHoldingPnl(row.unrealized, row.pnlPct)],
    ['持有时长', formatHoldSpan(row.holdDays, row.holdUnit)],
    ['仓位占比', weight == null ? '—' : `${(weight * 100).toFixed(1)}%`],
  ] : [];
  const buyNote = String(row?.note || '').trim();

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="持仓明细"
      size="sm"
      actions={(
        <>
          {onOpenKline ? (
            <Button variant="glass" onClick={onOpenKline}>查看数据</Button>
          ) : null}
          <Button variant="primary" onClick={onClose}>关闭</Button>
        </>
      )}
    >
      <DefinitionList
        items={kv.map(([label, value]) => ({ label, value }))}
      />
      {buyNote ? (
        <>
          <span className="ntq-decision-subtitle ntq-decision-strong">
            买入笔记
          </span>
          <span className="decision-buy-note">
            {buyNote}
          </span>
        </>
      ) : null}
      <span className="ntq-decision-subtitle ntq-decision-strong">
        目标
      </span>
      <div className="ntq-caption ntq-muted">
        已按某档卖出的会标已完成；剩下的股仍按当前浮动盈亏显示，不会因为还在列表里就把该档当成没做过。
      </div>
      {row?.goals?.length ? (
        <div className="decision-goal-list">
          {row.goals.map((goal, index) => (
            <div key={`${goal.kind}-${index}`} className="decision-goal-row">
              <span className="decision-goal-row__text">
                {goal.text}
              </span>
              <Tag size="sm" status={({success:"success",warning:"warning",error:"error",info:"info",default:"neutral",primary:"info"})[goal.done ? 'success' : 'warning']||"neutral"} variant="outline">{goal.done ? '已完成' : '未完成'}</Tag>
            </div>
          ))}
        </div>
      ) : (
        <span className="ntq-muted">本策略未配置持仓目标</span>
      )}
    </Dialog>
  );
}
