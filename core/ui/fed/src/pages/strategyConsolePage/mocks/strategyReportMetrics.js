/**
 * 将 executionState / 对比版本 mock 转为各报告用 metrics（API 对接时在此层换实现）
 */
import {
  MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION,
  MOCK_REPORT_PRICE_SUMMARIES_BY_VERSION,
} from './strategyWorkbenchMocks';

export function buildEnumMetricsFromTotal(totalOpportunities) {
  if (totalOpportunities <= 0) return null;

  const totalStocks = 150;
  const triggerStocks = Math.max(1, Math.round(totalOpportunities * 0.42));
  const triggerRatio = Number(((triggerStocks / totalStocks) * 100).toFixed(1));
  const avgPerStock = totalOpportunities / triggerStocks;
  const p10 = Math.max(0.4, Number((avgPerStock * 0.38).toFixed(2)));
  const p20 = Math.max(0.5, Number((avgPerStock * 0.48).toFixed(2)));
  const p30 = Math.max(0.6, Number((avgPerStock * 0.62).toFixed(2)));
  const p40 = Math.max(0.7, Number((avgPerStock * 0.76).toFixed(2)));
  const p50 = Number((avgPerStock * 0.9).toFixed(2));
  const p60 = Number((avgPerStock * 1.04).toFixed(2));
  const p70 = Number((avgPerStock * 1.2).toFixed(2));
  const p75 = Number((avgPerStock * 1.35).toFixed(2));
  const p80 = Number((avgPerStock * 1.5).toFixed(2));
  const p90 = Number((avgPerStock * 1.72).toFixed(2));
  const completedRatio = Number((58 + Math.min(30, totalOpportunities / 5)).toFixed(1));
  const completedCount = Math.round((completedRatio / 100) * totalOpportunities);

  const meanGap = Number((6 + (120 / Math.max(20, totalOpportunities))).toFixed(2));
  const meanDuration = Number((4 + totalOpportunities / 18).toFixed(2));
  const stdGap = Number((meanGap * 0.62).toFixed(2));
  const cv = Number((stdGap / meanGap).toFixed(2));

  const dispersionConclusion = cv < 0.45
    ? '机会出现较均匀，节奏相对稳定'
    : (cv < 0.8 ? '机会有一定聚集，节奏波动中等' : '机会集中出现，节奏波动较大');

  const percentileLabels = ['10%分位', '20%分位', '30%分位', '40%分位', '50%分位', '60%分位', '70%分位', '80%分位', '90%分位'];
  const percentileValues = [p10, p20, p30, p40, p50, p60, p70, p80, p90];

  return {
    totalOpportunities,
    totalStocks,
    triggerStocks,
    triggerRatio,
    avgPerStock,
    p10,
    p20,
    p30,
    p40,
    p50,
    p60,
    p70,
    p75,
    p80,
    p90,
    completedRatio,
    completedCount,
    meanGap,
    meanDuration,
    stdGap,
    cv,
    dispersionConclusion,
    percentileLabels,
    percentileValues,
  };
}

export function buildEnumMetrics(executionState) {
  const totalOpportunities = Number(executionState?.result?.enum?.opportunities || 0);
  return buildEnumMetricsFromTotal(totalOpportunities);
}

export function buildPriceMetricsFromBase(base) {
  if (!base) return null;
  const winRate = Number(base.winRate || 0);
  const avgRoi = Number(base.roi || 0);
  const avgDurationDays = Number(base.avgHoldDays || 0);

  const totalInvestments = Math.max(18, Math.round(36 + winRate * 1.4));
  const totalWinInvestments = Math.round(totalInvestments * (winRate / 100));
  const totalLossInvestments = Math.max(0, totalInvestments - totalWinInvestments - 2);
  const totalOpenInvestments = totalInvestments - totalWinInvestments - totalLossInvestments;
  const stocksWithOpportunities = Math.max(8, Math.round(totalInvestments / 2.8));
  const avgInvestmentsPerStock = Number((totalInvestments / stocksWithOpportunities).toFixed(2));

  const annualReturn = avgDurationDays > 0
    ? Number((avgRoi * (365 / avgDurationDays)).toFixed(2))
    : 0;
  const avgProfitPerInvestment = Math.round(12000 + avgRoi * 1400);
  const avgProfitPerStock = Math.round(avgProfitPerInvestment * avgInvestmentsPerStock);

  const roiP10 = Number((avgRoi * 0.28).toFixed(2));
  const roiP20 = Number((avgRoi * 0.42).toFixed(2));
  const roiP30 = Number((avgRoi * 0.58).toFixed(2));
  const roiP40 = Number((avgRoi * 0.73).toFixed(2));
  const roiP50 = Number((avgRoi * 0.92).toFixed(2));
  const roiP60 = Number((avgRoi * 1.07).toFixed(2));
  const roiP70 = Number((avgRoi * 1.22).toFixed(2));
  const roiP80 = Number((avgRoi * 1.38).toFixed(2));
  const roiP90 = Number((avgRoi * 1.55).toFixed(2));
  const roiP25 = Number(((roiP20 + roiP30) / 2).toFixed(2));
  const roiP75 = Number(((roiP70 + roiP80) / 2).toFixed(2));
  const roiIqr = Number((roiP75 - roiP25).toFixed(2));
  const roiBucketEdges = [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50];
  const roiBucketLabels = roiBucketEdges.slice(0, -1).map((start, index) => {
    const end = roiBucketEdges[index + 1];
    return `${start}%~${end}%`;
  });
  const sigma = 18;
  const roiBucketWeights = roiBucketEdges.slice(0, -1).map((start, index) => {
    const center = (start + roiBucketEdges[index + 1]) / 2;
    return Math.exp(-((center - avgRoi) ** 2) / (2 * sigma * sigma));
  });
  const weightSum = roiBucketWeights.reduce((sum, weight) => sum + weight, 0) || 1;
  const rawCounts = roiBucketWeights.map((weight) => (weight / weightSum) * totalInvestments);
  const roiBucketCounts = rawCounts.map((value) => Math.floor(value));
  let remaining = totalInvestments - roiBucketCounts.reduce((sum, count) => sum + count, 0);
  const remainders = rawCounts
    .map((value, index) => ({ index, remainder: value - Math.floor(value) }))
    .sort((a, b) => b.remainder - a.remainder);
  for (let i = 0; i < remainders.length && remaining > 0; i += 1) {
    roiBucketCounts[remainders[i].index] += 1;
    remaining -= 1;
  }

  const roiConclusion = roiP50 > 0 && roiP25 > 0
    ? '中位与下分位均为正，收益结构较稳'
    : (roiP50 > 0 ? '中位收益为正，但下分位承压' : '中位收益偏弱，需关注策略有效性');

  return {
    winRate: Number(winRate.toFixed(1)),
    avgRoi: Number(avgRoi.toFixed(2)),
    avgDurationDays: Number(avgDurationDays.toFixed(1)),
    annualReturn,
    totalInvestments,
    totalWinInvestments,
    totalLossInvestments,
    totalOpenInvestments,
    stocksWithOpportunities,
    avgInvestmentsPerStock,
    avgProfitPerInvestment,
    avgProfitPerStock,
    roiP10,
    roiP20,
    roiP30,
    roiP40,
    roiP50,
    roiP60,
    roiP70,
    roiP80,
    roiP90,
    roiP25,
    roiP75,
    roiIqr,
    roiConclusion,
    roiBucketLabels,
    roiBucketCounts,
    roiPercentileLabels: ['10%分位', '20%分位', '30%分位', '40%分位', '50%分位', '60%分位', '70%分位', '80%分位', '90%分位'],
    roiPercentileValues: [roiP10, roiP20, roiP30, roiP40, roiP50, roiP60, roiP70, roiP80, roiP90],
  };
}

export function buildPriceMetrics(executionState) {
  const base = executionState?.result?.price || MOCK_REPORT_PRICE_SUMMARIES_BY_VERSION.latest;
  return buildPriceMetricsFromBase(base);
}

export function buildCapitalMetricsFromBase(base) {
  if (!base) return null;
  const initialCapital = 1_000_000;
  const totalReturnPct = Number(base.totalReturnPct || 0);
  const maxDrawdownPct = Number(base.maxDrawdownPct || 0);
  const winRatePct = Number(base.winRatePct || 0);

  const finalEquity = Math.round(initialCapital * (1 + totalReturnPct / 100));
  const totalProfit = finalEquity - initialCapital;
  const calmarRatio = maxDrawdownPct > 0 ? Number((totalReturnPct / maxDrawdownPct).toFixed(2)) : 0;

  const sellTrades = Math.max(80, Math.round(140 + winRatePct * 1.1));
  const buyTrades = sellTrades;
  const totalTrades = buyTrades + sellTrades;
  const winTrades = Math.round(sellTrades * (winRatePct / 100));
  const lossTrades = Math.max(0, sellTrades - winTrades);
  const avgPnlPerTrade = sellTrades > 0 ? Math.round(totalProfit / sellTrades) : 0;

  const peakPositions = 10;
  const avgOpenPositions = Number((peakPositions * (0.56 + winRatePct / 250)).toFixed(1));
  const fullExposureDaysRatio = Number((10 + winRatePct / 3).toFixed(1));
  const avgCashRatio = Number((34 - totalReturnPct * 0.45).toFixed(1));
  const capitalUtilizationRatio = Number((100 - avgCashRatio).toFixed(1));

  const maxLossStreak = Math.max(2, Math.round(9 - winRatePct / 10));
  const maxDrawdownDurationDays = Math.max(8, Math.round(42 - totalReturnPct / 1.8));
  const worstTradePnls = [
    -Math.round(initialCapital * (maxDrawdownPct / 100) * 0.17),
    -Math.round(initialCapital * (maxDrawdownPct / 100) * 0.14),
    -Math.round(initialCapital * (maxDrawdownPct / 100) * 0.11),
  ];

  const stockCount = Math.max(25, Math.round(46 + winRatePct / 2));
  const avgTradesPerStock = Number((sellTrades / stockCount).toFixed(2));
  const top5ContributionRatio = Number((34 + totalReturnPct * 0.5).toFixed(1));
  const stockPnlCv = Number((1.6 - totalReturnPct / 65).toFixed(2));

  const equityCurveLabels = ['T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11'];
  const equityRatios = [0, 0.03, 0.08, 0.06, 0.12, 0.16, 0.13, 0.21, 0.24, 0.22, 0.28, 0.318];
  const normalizedTarget = totalReturnPct / 100;
  const normalizedBase = 0.318;
  const equityCurveValues = equityRatios.map((ratio) => (
    Math.round(initialCapital * (1 + (ratio / normalizedBase) * normalizedTarget))
  ));
  const runningPeak = [];
  let peak = equityCurveValues[0];
  for (let i = 0; i < equityCurveValues.length; i += 1) {
    peak = Math.max(peak, equityCurveValues[i]);
    runningPeak.push(peak);
  }
  const drawdownCurveValues = equityCurveValues.map((value, index) => {
    const dd = runningPeak[index] > 0 ? ((runningPeak[index] - value) / runningPeak[index]) * 100 : 0;
    return Number(dd.toFixed(2));
  });
  const maxDrawdownRealized = Math.max(...drawdownCurveValues, maxDrawdownPct);
  const maxDrawdownDisplay = Number(maxDrawdownRealized.toFixed(2));

  return {
    initialCapital,
    finalEquity,
    totalProfit,
    totalReturnPct: Number(totalReturnPct.toFixed(2)),
    maxDrawdownPct: maxDrawdownDisplay,
    calmarRatio,
    totalTrades,
    buyTrades,
    sellTrades,
    winTrades,
    lossTrades,
    winRatePct: Number(winRatePct.toFixed(2)),
    avgPnlPerTrade,
    avgOpenPositions,
    peakPositions,
    fullExposureDaysRatio,
    avgCashRatio,
    capitalUtilizationRatio,
    maxLossStreak,
    maxDrawdownDurationDays,
    worstTradePnls,
    stockCount,
    avgTradesPerStock,
    top5ContributionRatio,
    stockPnlCv,
    equityCurveLabels,
    equityCurveValues,
    drawdownCurveValues,
  };
}

export function buildCapitalMetrics(executionState) {
  const summary = executionState?.result?.capital;
  const parsed = summary
    ? {
      totalReturnPct: Number((Number(summary.totalReturn || 0) * 100).toFixed(2)),
      maxDrawdownPct: Number((Number(summary.maxDrawdown || 0) * 100).toFixed(2)),
      winRatePct: Number((Number(summary.winRate || 0) * 100).toFixed(2)),
    }
    : null;
  const hasRealCapitalMetrics = Boolean(
    parsed && (Math.abs(parsed.totalReturnPct) > 0 || Math.abs(parsed.maxDrawdownPct) > 0 || Math.abs(parsed.winRatePct) > 0),
  );
  const base = hasRealCapitalMetrics ? parsed : MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION.latest;
  return buildCapitalMetricsFromBase(base);
}
