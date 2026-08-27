import React from 'react';
import MetricCard from 'components/metricCard/metricCard';
import MetricGrid from 'components/metricGrid/metricGrid';

const BASE_SKIP_ITEMS = [
  { key: 'skippedBuyAtLimitUp', title: '涨停跳过买入' },
  { key: 'skippedSellAtLimitDown', title: '跌停跳过卖出' },
  { key: 'skippedStockStatus', title: '状态跳过投资' },
];

const PARTICIPATION_SKIP_ITEMS = [
  { key: 'skippedBuyParticipation', title: '参与率跳过买入' },
  { key: 'skippedSellParticipation', title: '参与率跳过卖出' },
  { key: 'clippedBuyParticipation', title: '参与率缩量买入' },
  { key: 'clippedSellParticipation', title: '参与率缩量卖出' },
];

function countValue(metrics, key) {
  const n = Number(metrics?.[key]);
  return (Number.isFinite(n) ? n : 0).toLocaleString();
}

/** 价格 / 资金共用的成交跳过卡片；资金层再带上参与率几项。 */
function ExecutionSkipCards({ metrics, tips, includeParticipation = false }) {
  const items = includeParticipation
    ? [...BASE_SKIP_ITEMS, ...PARTICIPATION_SKIP_ITEMS]
    : BASE_SKIP_ITEMS;
  return (
    <MetricGrid columns={3}>
      {items.map((item) => (
        <MetricCard
          key={item.key}
          title={item.title}
          titleTip={tips?.[item.key]}
          value={countValue(metrics, item.key)}
        />
      ))}
    </MetricGrid>
  );
}

export default ExecutionSkipCards;
