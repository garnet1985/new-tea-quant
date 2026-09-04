import React from 'react';
import { Stack, Typography } from '@mui/material';
import ChartPanel from 'components/chartPanel/chartPanel';
import MetricCard from 'components/metricCard/metricCard';
import MetricGrid from 'components/metricGrid/metricGrid';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import {
  CAPITAL_CHART_TIPS,
  CAPITAL_METRIC_TIPS,
  CAPITAL_SECTION_TIPS,
  REPORT_STOCK_GRID_TIPS,
} from '../reportMetricTips';
import ReportUnavailableHint from '../components/reportUnavailableHint';
import ReportStockGridSection from '../components/reportStockGridSection';
import ExecutionSkipCards from '../components/executionSkipCards';
import { useReportStockSearch } from '../hooks/useReportStockSearch';
import { STOCK_NAME_COLUMN, stockCodeColumn } from '../lib/reportStockColumns';
import { formatReportMoney } from '../lib/formatReportMoney';
import { buildPortfolioEventChartOption } from '../lib/portfolioEventChart';

function formatRiskRatio(value) {
  if (!Number.isFinite(value)) return '—';
  return Number(value).toFixed(2);
}

function CapitalAllocationReport({
  metrics,
  stockRows,
  title = '投资模拟报告',
  showStockGrid = true,
  hideTitle = false,
}) {
  const { stockSearch, setStockSearch, derivedStockRows, filteredRows } = useReportStockSearch(stockRows);

  const stockColumns = [
    stockCodeColumn(),
    STOCK_NAME_COLUMN,
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
      valueFormatter: (params) => `${params.value >= 0 ? '+' : ''}${formatReportMoney(params.value)}`,
    },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
  ];

  if (!metrics || typeof metrics !== 'object') {
    return <ReportUnavailableHint />;
  }

  const executionSkipsAvail = metrics?._availability?.executionSkips ?? false;

  const showStockSampleGrid = Boolean(showStockGrid && derivedStockRows.length > 0);

  return (
    <Stack spacing={1.25}>
      {!hideTitle ? (
        <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>
      ) : null}

      {showStockSampleGrid ? (
        <ReportStockGridSection
          filteredRows={filteredRows}
          hideWhenEmpty={false}
          title="逐股样本"
          tip={REPORT_STOCK_GRID_TIPS.portfolio}
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="资金结果总览"
        tip={CAPITAL_SECTION_TIPS.overview}
      >
        <MetricGrid columns={3}>
          <MetricCard
            title="初始资金"
            titleTip={CAPITAL_METRIC_TIPS.initialCapital}
            value={formatReportMoney(metrics.initialCapital)}
          />
          <MetricCard
            title="最终总资产"
            titleTip={CAPITAL_METRIC_TIPS.finalEquity}
            value={formatReportMoney(metrics.finalEquity)}
          />
          <MetricCard
            title="总收益率"
            titleTip={CAPITAL_METRIC_TIPS.totalReturnPct}
            value={`${metrics.totalReturnPct}%`}
          />
          <MetricCard
            title="收益回撤比（Calmar）"
            titleTip={CAPITAL_METRIC_TIPS.calmarRatio}
            value={formatRiskRatio(metrics.calmarRatio)}
          />
        </MetricGrid>
        <ChartPanel
          title="资产与回撤"
          note="上：总资产 · 下：回撤（相对历史最高净值，不是本金）"
          tip={CAPITAL_CHART_TIPS.equityEventCurve}
          option={buildPortfolioEventChartOption(metrics)}
          height={380}
        />
      </SectionBlock>

      <SectionBlock
        title="交易质量"
        tip={CAPITAL_SECTION_TIPS.tradeQuality}
      >
        <MetricGrid>
          <MetricCard
            title="总交易次数"
            titleTip={CAPITAL_METRIC_TIPS.totalTrades}
            value={metrics.totalTrades.toLocaleString()}
            hint={`买入 ${metrics.buyTrades} / 卖出 ${metrics.sellTrades}`}
          />
          <MetricCard
            title="胜率"
            titleTip={CAPITAL_METRIC_TIPS.winRate}
            value={`${metrics.winRatePct}%`}
            hint={`盈利 ${metrics.winTrades} / 亏损 ${metrics.lossTrades}`}
          />
          <MetricCard
            title="总盈亏金额"
            titleTip={CAPITAL_METRIC_TIPS.totalProfit}
            value={formatReportMoney(metrics.totalProfit)}
          />
          <MetricCard
            title="单笔平均盈亏"
            titleTip={CAPITAL_METRIC_TIPS.avgPnlPerTrade}
            value={formatReportMoney(metrics.avgPnlPerTrade)}
          />
        </MetricGrid>
      </SectionBlock>

      <SectionBlock
        title="成交跳过统计"
        tip={CAPITAL_SECTION_TIPS.executionSkips}
      >
        {executionSkipsAvail ? (
          <ExecutionSkipCards
            metrics={metrics}
            tips={CAPITAL_METRIC_TIPS}
            includeParticipation
          />
        ) : <ReportUnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="仓位与资金利用率"
        tip={CAPITAL_SECTION_TIPS.utilization}
      >
        <MetricGrid>
          <MetricCard
            title="平均持仓数"
            titleTip={CAPITAL_METRIC_TIPS.avgOpenPositions}
            value={`${metrics.avgOpenPositions} / ${metrics.peakPositions}`}
          />
          <MetricCard
            title="满仓天数占比"
            titleTip={CAPITAL_METRIC_TIPS.fullExposureDaysRatio}
            value={`${metrics.fullExposureDaysRatio}%`}
          />
          <MetricCard
            title="平均现金占比"
            titleTip={CAPITAL_METRIC_TIPS.avgCashRatio}
            value={`${metrics.avgCashRatio}%`}
          />
          <MetricCard
            title="资金利用率"
            titleTip={CAPITAL_METRIC_TIPS.capitalUtilization}
            value={`${metrics.capitalUtilizationRatio}%`}
          />
        </MetricGrid>
      </SectionBlock>

      <SectionBlock
        title="风险结构"
        tip={CAPITAL_SECTION_TIPS.risk}
      >
        <MetricGrid>
          <MetricCard
            title="最大回撤"
            titleTip={CAPITAL_METRIC_TIPS.maxDrawdown}
            value={`${metrics.maxDrawdownPct}%`}
          />
          <MetricCard
            title="最大回撤持续天数"
            titleTip={CAPITAL_METRIC_TIPS.maxDrawdownDuration}
            value={`${metrics.maxDrawdownDurationDays} 天`}
          />
          <MetricCard
            title="最长连续亏损"
            titleTip={CAPITAL_METRIC_TIPS.maxLossStreak}
            value={`${metrics.maxLossStreak} 笔`}
          />
          <MetricCard
            title="Top3 单笔亏损"
            titleTip={CAPITAL_METRIC_TIPS.worstTradePnls}
            value={metrics.worstTradePnls.map((value) => formatReportMoney(value)).join(' / ')}
          />
        </MetricGrid>
      </SectionBlock>

      <SectionBlock
        title="股票集中度"
        tip={CAPITAL_SECTION_TIPS.concentration}
      >
        <MetricGrid>
          <MetricCard
            title="触发股票数"
            titleTip={CAPITAL_METRIC_TIPS.stockCount}
            value={metrics.stockCount.toLocaleString()}
          />
          <MetricCard
            title="每股平均交易次数"
            titleTip={CAPITAL_METRIC_TIPS.avgTradesPerStock}
            value={metrics.avgTradesPerStock.toFixed(2)}
          />
          <MetricCard
            title="前 5 股票收益贡献占比"
            titleTip={CAPITAL_METRIC_TIPS.top5ContributionRatio}
            value={`${metrics.top5ContributionRatio}%（共 ${metrics.stockCount.toLocaleString()} 股）`}
          />
          <MetricCard
            title="股票收益离散系数（CV）"
            titleTip={CAPITAL_METRIC_TIPS.stockPnlCv}
            value={metrics.stockPnlCv}
          />
        </MetricGrid>
      </SectionBlock>
    </Stack>
  );
}

export default CapitalAllocationReport;
