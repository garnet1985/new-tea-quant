import React from 'react';
import { Tag } from 'ui';
import { isHttpStatusError } from 'service/request';
import {
  formatMoney,
  formatSignedMoney,
  mapStockStatusTags,
  statusChipClassName,
} from './decisionFormat';

export function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function resolveLiveStatus(ticker, liveById, loading) {
  const id = String(ticker || '').trim();
  if (!id) return { tags: [], loading: false };
  if (Object.prototype.hasOwnProperty.call(liveById || {}, id)) {
    return { tags: liveById[id] || [], loading: false };
  }
  return { tags: [], loading: Boolean(loading) };
}

export function formatDrawdown(value) {
  if (value == null || !Number.isFinite(Number(value))) return '至今无回撤';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

export function formatHoldingPnl(unrealized, pnlPct) {
  if (unrealized == null || !Number.isFinite(Number(unrealized))) return '—';
  const money = formatSignedMoney(unrealized);
  if (pnlPct == null || !Number.isFinite(Number(pnlPct))) return money;
  const n = Number(pnlPct) * 100;
  const sign = n > 0 ? '+' : '';
  return `${money}（${sign}${n.toFixed(1)}%）`;
}

export function formatHoldingListPnl(unrealized) {
  if (unrealized == null || !Number.isFinite(Number(unrealized))) return '—';
  const n = Number(unrealized);
  if (n >= 0) return `+${formatMoney(n)}`;
  return formatMoney(n);
}

export function holdingPnlTone(unrealized) {
  return Number(unrealized) < 0 ? 'is-loss' : 'is-profit';
}

export function formatMarketValueWithPnl(marketValue, unrealized) {
  if (marketValue == null || !Number.isFinite(Number(marketValue))) return '—';
  const value = formatMoney(marketValue);
  if (unrealized == null || !Number.isFinite(Number(unrealized))) return value;
  return (
    <>
      {value}
      {' '}
      <span className={`decision-pnl ${holdingPnlTone(unrealized)}`}>
        ({formatSignedMoney(unrealized)})
      </span>
    </>
  );
}

export function StockStatusChips({ tags, loading = false }) {
  if (loading) {
    return (
      <span className="decision-status-chips is-loading" aria-busy="true" title="状态确认中">
        <span className="decision-status-chip-skeleton" />
      </span>
    );
  }
  const items = mapStockStatusTags(tags);
  if (!items.length) return null;
  return (
    <span className="decision-status-chips">
      {items.map((item) => (
        <Tag key={item.tag} className={`decision-status-chip ${statusChipClassName(item.tag)}`} size="sm" status="neutral" variant="outline">{item.label}</Tag>
      ))}
    </span>
  );
}

export function holdingStockLabel(row) {
  const name = String(row?.name || '').trim();
  const ticker = String(row?.ticker || '').trim();
  if (name && ticker) return `${name}  ${ticker}`;
  return name || ticker || '—';
}

export function opportunityStockLabel(row) {
  const name = String(row?.name || '').trim();
  const ticker = String(row?.ticker || '').trim();
  if (name && ticker) return `${name}（${ticker}）`;
  return name || ticker || '—';
}

export function inferAShareLot(ticker) {
  // 与 china_a_stock 手数表对齐：现场 lot_step 未到时也能步进。
  const id = String(ticker || '').split('.')[0];
  if (/^688/.test(id)) return { minLot: 200, lotStep: 1 };
  if (/^(8|43|92)/.test(id)) return { minLot: 100, lotStep: 1 };
  return { minLot: 100, lotStep: 100 };
}

export function lotRule(row) {
  const inferred = inferAShareLot(row?.ticker);
  const minLot = Number(row?.lotSize) > 0 ? Number(row.lotSize) : inferred.minLot;
  const lotStep = Number(row?.lotStep) > 0 ? Number(row.lotStep) : inferred.lotStep;
  return { minLot, lotStep };
}

export function shareStepJump(lotStep) {
  const step = Math.max(1, Number(lotStep) || 1);
  return step >= 100 ? step : 100;
}

export function stepShares(current, direction, minLot, lotStep) {
  const min = Math.max(1, Number(minLot) || 1);
  const jump = shareStepJump(lotStep);
  const n = Math.max(0, Math.trunc(Number(current) || 0));
  if (direction > 0) {
    if (n < min) return min;
    return n + jump;
  }
  if (n <= min) return 0;
  const next = n - jump;
  return next < min ? min : next;
}

export function validateShareDraft(raw, minLot, lotStep) {
  const text = String(raw ?? '').trim();
  if (!text) return { ok: true, shares: 0 };
  if (!/^\d+$/.test(text)) return { ok: false, message: '股数须为整数' };
  const shares = Number(text);
  if (!Number.isInteger(shares) || shares < 0) return { ok: false, message: '股数须为整数' };
  if (shares === 0) return { ok: true, shares: 0 };
  const min = Math.max(1, Number(minLot) || 1);
  const step = Math.max(1, Number(lotStep) || min);
  if (shares < min) return { ok: false, message: `最少 ${min} 股` };
  if ((shares - min) % step !== 0) {
    return { ok: false, message: `须为 ${min} 起、每 ${step} 股` };
  }
  return { ok: true, shares };
}

export function cashFromShares(shares, price) {
  const n = Number(shares) || 0;
  const px = Number(price) || 0;
  if (n <= 0 || px <= 0) return 0;
  return n * px;
}

export function headerWithTooltip(label, title) {
  return () => (
    <span className="decision-col-help" title={title}>{label}</span>
  );
}

export function suggestedBuyTooltip(mode) {
  if (mode === 'equal_shares') {
    return '等股：每次买入手数 × 最小交易单位。投资弹窗里可填入该建议。';
  }
  if (mode === 'kelly') {
    return '凯利：当前现金 × 该标的截至当前日的胜率 × 凯利折扣。无已完成样本为 —。投资弹窗里可填入该建议。';
  }
  return '等价资金：初始资金 ÷ 最大持股数，再按手数折股。投资弹窗里可填入该建议。';
}
