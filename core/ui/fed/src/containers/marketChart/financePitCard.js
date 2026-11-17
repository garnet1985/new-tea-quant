import React from 'react';
import { MARKET_CHART_GRID_LEFT, MARKET_CHART_GRID_RIGHT } from './theme';
import { formatMarketChartDateLabel } from './dateFormat';
import './financePitCard.scss';

const METRIC_DEFS = [
  ['ROE', 'roe'],
  ['EPS', 'eps'],
  ['毛利率', 'gross_profit_margin'],
  ['营收同比', 'or_yoy'],
  ['净利同比', 'netprofit_yoy'],
];

/**
 * 财报 PIT 快照卡：方块常驻；未悬停显示 --，悬停十字线后填数。
 */
export default function FinancePitCard({
  visible = false,
  live = false,
  pointerAsOf = '',
  snapshot = null,
}) {
  if (!visible) return null;
  const snap = snapshot?.snapshot || {};
  const asOfLabel = formatMarketChartDateLabel(pointerAsOf);
  const annLabel = formatMarketChartDateLabel(snapshot?.date);
  return (
    <div
      className="ntq-finance-pit-card"
      style={{
        marginLeft: `${MARKET_CHART_GRID_LEFT}px`,
        marginRight: `${MARKET_CHART_GRID_RIGHT}px`,
      }}
    >
      <p className="ntq-finance-pit-card__caption">
        {live
          ? [
            '财报快照（PIT）',
            asOfLabel ? `as-of ${asOfLabel}` : '',
            snapshot?.quarter || '',
            annLabel ? `公告 ${annLabel}` : '',
          ].filter(Boolean).join(' · ')
          : '财报快照（悬停 K 线查看 PIT）'}
      </p>
      <div className="ntq-finance-pit-card__metrics">
        {METRIC_DEFS.map(([name, key]) => {
          const raw = live ? snap?.[key] : null;
          const n = Number(raw);
          const filled = live && raw != null && Number.isFinite(n);
          const text = filled ? n.toFixed(2) : '--';
          const valueClass = [
            'ntq-finance-pit-card__value',
            !filled ? 'is-empty' : '',
            filled && n < 0 ? 'is-neg' : '',
          ].filter(Boolean).join(' ');
          return (
            <div key={name} className="ntq-finance-pit-card__metric">
              <span className="ntq-finance-pit-card__metric-name">{name}</span>
              <span className={valueClass}>{text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
