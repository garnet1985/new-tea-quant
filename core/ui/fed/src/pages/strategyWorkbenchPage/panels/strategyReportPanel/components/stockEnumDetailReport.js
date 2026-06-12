import React from 'react';
import { Box } from '@mui/material';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import { ENUM_METRIC_TIPS } from '../reportMetricTips';
import ReportUnavailableHint from './reportUnavailableHint';

const SINGLE_STOCK_ENUM_SECTION_TIP =
  '该股在枚举阶段的汇总指标；触发日在上方 K 线图中标注。';

function StockEnumDetailReport({ metrics }) {
  const avail = metrics?._availability ?? {};

  if (!metrics || typeof metrics !== 'object') {
    return <ReportUnavailableHint />;
  }

  const hasAny = avail.overview || avail.tradability || avail.timing;
  if (!hasAny) {
    return <ReportUnavailableHint />;
  }

  return (
    <SectionBlock title="枚举统计" tip={SINGLE_STOCK_ENUM_SECTION_TIP}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          gap: 1,
        }}
      >
        {avail.overview ? (
          <>
            <MetricCard
              title="机会总数"
              titleTip={ENUM_METRIC_TIPS.totalOpportunities}
              value={`${metrics.totalOpportunities.toLocaleString()} 个`}
            />
            <MetricCard
              title="机会完成度"
              titleTip={ENUM_METRIC_TIPS.completeness}
              value={`${metrics.completedCount.toLocaleString()} / ${metrics.totalOpportunities.toLocaleString()} (${metrics.completedRatio}%)`}
            />
            {avail.winRate ? (
              <MetricCard
                title="机会胜率"
                titleTip={ENUM_METRIC_TIPS.winRate}
                value={`${metrics.winRate}%`}
                hint={`${metrics.winCount} 胜 / ${metrics.lossCount} 负（共 ${metrics.winRateSampleCount} 笔已完成）`}
              />
            ) : null}
          </>
        ) : null}

        {avail.tradability ? (
          <>
            <MetricCard
              title="涨停无法买入"
              titleTip={ENUM_METRIC_TIPS.limitUpBuy}
              value={`${metrics.buyAtLimitUpCount.toLocaleString()} / ${metrics.buyTradabilitySampleCount.toLocaleString()}`}
              hint={`占比 ${metrics.limitUpBuyRatio}%`}
            />
            <MetricCard
              title="跌停无法卖出"
              titleTip={ENUM_METRIC_TIPS.limitDownSell}
              value={`${metrics.sellAtLimitDownCount.toLocaleString()} / ${metrics.sellTradabilitySampleCount.toLocaleString()}`}
              hint={`占比 ${metrics.limitDownSellRatio}%`}
            />
          </>
        ) : null}

        {avail.timing ? (
          <>
            <MetricCard
              title="平均每股机会持续（天）"
              titleTip={ENUM_METRIC_TIPS.meanDuration}
              value={`${metrics.meanDuration} 天`}
            />
            <MetricCard
              title="机会分散度"
              titleTip={ENUM_METRIC_TIPS.dispersion}
              value={Number.isFinite(Number(metrics.stdGap))
                ? `SD ${metrics.stdGap} 天`
                : '—'}
              hint={[
                Number.isFinite(Number(metrics.cv)) ? `CV ${metrics.cv}` : null,
                (metrics.dispersionConclusion && String(metrics.dispersionConclusion).trim()) || null,
              ].filter(Boolean).join(' · ') || undefined}
            />
          </>
        ) : null}
      </Box>
    </SectionBlock>
  );
}

export default StockEnumDetailReport;
