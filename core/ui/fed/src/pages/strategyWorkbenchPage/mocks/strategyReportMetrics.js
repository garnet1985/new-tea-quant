/**
 * 策略报告 metrics：价格/资金仍可能带推导字段；**枚举**仅以快照/API 字段为准，不合成草图数据。
 */
import { MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION } from './strategyWorkbenchMocks';

/** 枚举报告某结果块缺少所需字段时的统一提示 */
export const REPORT_BLOCK_UNAVAILABLE_ZH = '数据异常，无法显示该结果。';

function mergeEnumSlot(summary) {
  if (!summary || typeof summary !== 'object') return null;
  const { enumMetrics, ...rest } = summary;
  const inner = enumMetrics && typeof enumMetrics === 'object' ? enumMetrics : {};
  return { ...inner, ...rest };
}

function normalizePercent(raw) {
  const n = Number(raw ?? 0);
  if (!Number.isFinite(n)) return NaN;
  if (n <= 0) return 0;
  return n <= 1 ? Number((n * 100).toFixed(1)) : Number(n.toFixed(1));
}

function toNumberList(arr) {
  return Array.isArray(arr) ? arr.map((v) => Number(v ?? 0)) : [];
}

function toStringList(arr) {
  return Array.isArray(arr) ? arr.map((v) => String(v ?? '')) : [];
}

/**
 * 将 ``result_report.enum`` 槽位（可与 ``enumMetrics`` 嵌套并存）规范为扁平 metrics，并标记各展示块是否数据齐全。
 * 不做数值臆造；缺字段时对应块由 UI 显示 ``REPORT_BLOCK_UNAVAILABLE_ZH``。
 */
export function normalizeEnumMetricsFromSummary(summary) {
  const m = mergeEnumSlot(summary);
  if (!m || typeof m !== 'object') return null;

  const pick = (camel, snake) => {
    if (m[camel] !== undefined && m[camel] !== null) return m[camel];
    return m[snake];
  };

  let totalOpportunities = Number(pick('totalOpportunities', 'total_opportunities') ?? 0);
  if (!Number.isFinite(totalOpportunities) || totalOpportunities <= 0) {
    const alt = Number(pick('opportunities', 'opportunity_count'));
    if (Number.isFinite(alt) && alt > 0) totalOpportunities = alt;
  }
  const totalStocks = Number(pick('totalStocks', 'total_stocks') ?? 0);

  let triggerStocks = Number(pick('triggerStocks', 'trigger_stocks'));
  let triggerRatio = Number(pick('triggerRatio', 'trigger_ratio'));
  if (!Number.isFinite(triggerRatio) && totalStocks > 0 && Number.isFinite(triggerStocks)) {
    triggerRatio = Number(((triggerStocks / totalStocks) * 100).toFixed(1));
  }

  let avgPerStock = Number(pick('avgPerStock', 'avg_per_stock'));
  if (!Number.isFinite(avgPerStock) && triggerStocks > 0 && Number.isFinite(totalOpportunities)) {
    avgPerStock = Number((totalOpportunities / triggerStocks).toFixed(2));
  }

  let completedRatio = normalizePercent(pick('completedRatio', 'completed_ratio'));
  if (!Number.isFinite(completedRatio) || completedRatio === 0) {
    const alt = normalizePercent(pick('completionRate', 'completion_rate'));
    if (Number.isFinite(alt) && alt > 0) completedRatio = alt;
  }

  let completedCount = Number(pick('completedCount', 'completed_count'));
  if (
    !Number.isFinite(completedCount)
    && Number.isFinite(completedRatio)
    && Number.isFinite(totalOpportunities)
  ) {
    completedCount = Math.round((completedRatio / 100) * totalOpportunities);
  }

  const unfinishedCount = Number(pick('unfinishedCount', 'unfinished_count'));

  let opportunityCountLabels = toStringList(pick('opportunityCountLabels', 'opportunity_count_labels'));
  let opportunityCountStockCounts = toNumberList(pick('opportunityCountStockCounts', 'opportunity_count_stock_counts'));
  let opportunityCountStockRatios = toNumberList(pick('opportunityCountStockRatios', 'opportunity_count_stock_ratios'));

  const opportunityCountMin = Number(pick('opportunityCountMin', 'opportunity_count_min') ?? 0);
  const opportunityCountMax = Number(pick('opportunityCountMax', 'opportunity_count_max') ?? 0);
  const opportunityCountBucketCount = Number(
    pick('opportunityCountBucketCount', 'opportunity_count_bucket_count') ?? opportunityCountLabels.length,
  );

  const countSum = opportunityCountStockCounts.reduce((s, c) => s + Number(c || 0), 0);
  const stockDenom = totalStocks > 0 ? totalStocks : countSum;
  if (
    opportunityCountLabels.length > 0
    && opportunityCountStockCounts.length === opportunityCountLabels.length
    && opportunityCountStockRatios.length !== opportunityCountLabels.length
    && stockDenom > 0
  ) {
    opportunityCountStockRatios = opportunityCountStockCounts.map((c) => (
      Number(((Number(c || 0) / stockDenom) * 100).toFixed(2))
    ));
  }

  const meanGap = Number(pick('meanGap', 'mean_gap'));
  const meanDuration = Number(pick('meanDuration', 'mean_duration'));
  const stdGap = Number(pick('stdGap', 'std_gap'));
  const cv = Number(pick('cv', 'cv'));
  const dispersionConclusion = String(pick('dispersionConclusion', 'dispersion_conclusion') ?? '');

  const percentileLabels = toStringList(pick('percentileLabels', 'percentile_labels'));
  const percentileValues = toNumberList(pick('percentileValues', 'percentile_values'));

  const hasPayload = (Number.isFinite(totalOpportunities) && totalOpportunities > 0)
    || (Number.isFinite(totalStocks) && totalStocks > 0)
    || opportunityCountLabels.length > 0
    || [meanGap, meanDuration].some((x) => Number.isFinite(Number(x)));

  if (!hasPayload) return null;

  const overviewOk = Number.isFinite(totalOpportunities)
    && Number.isFinite(totalStocks)
    && totalStocks > 0
    && totalOpportunities >= 0
    && (Number.isFinite(completedCount) || Number.isFinite(completedRatio));

  const stockStatsOk = Number.isFinite(totalStocks)
    && totalStocks > 0
    && Number.isFinite(triggerStocks)
    && Number.isFinite(avgPerStock);

  const distributionOk = opportunityCountLabels.length > 0
    && opportunityCountStockCounts.length === opportunityCountLabels.length
    && opportunityCountStockRatios.length === opportunityCountLabels.length;

  const timingOk = [meanGap, meanDuration, stdGap, cv].every((x) => Number.isFinite(Number(x)));

  return {
    totalOpportunities,
    totalStocks,
    triggerStocks,
    triggerRatio,
    avgPerStock: Number.isFinite(avgPerStock) ? avgPerStock : NaN,
    completedRatio: Number.isFinite(completedRatio) ? completedRatio : 0,
    completedCount: Number.isFinite(completedCount) ? completedCount : 0,
    unfinishedCount: Number.isFinite(unfinishedCount) ? unfinishedCount : 0,
    opportunityCountMin,
    opportunityCountMax,
    opportunityCountBucketCount,
    opportunityCountLabels,
    opportunityCountStockCounts,
    opportunityCountStockRatios,
    meanGap,
    meanDuration,
    stdGap,
    cv,
    dispersionConclusion,
    percentileLabels,
    percentileValues,
    _availability: {
      overview: overviewOk,
      stockStats: stockStatsOk,
      distribution: distributionOk,
      timing: timingOk,
    },
  };
}

export function buildEnumMetrics(executionState) {
  return normalizeEnumMetricsFromSummary(executionState?.result?.enum);
}

/**
 * 将 ``result_report.price_factor`` 槽位（与 ``PriceReport.to_dict()`` / ``0_session_summary.json`` 一致，snake_case）
 * 规范为 FED 展示用 metrics。ROI 分位、桶分布等**仅当**后端未来写入对应数组时才展示，否则对应区块由 UI 提示缺数。
 */
export function normalizePriceMetricsFromSummary(slot) {
  if (!slot || typeof slot !== 'object') return null;

  const m = { ...(slot.priceMetrics && typeof slot.priceMetrics === 'object' ? slot.priceMetrics : {}), ...slot };

  const firstNum = (keys) => {
    for (const k of keys) {
      if (m[k] === undefined || m[k] === null) continue;
      const n = Number(m[k]);
      if (Number.isFinite(n)) return n;
    }
    return NaN;
  };

  const toRatioAsPercent = (v) => {
    const x = Number(v);
    if (!Number.isFinite(x)) return NaN;
    if (x === 0) return 0;
    if (Math.abs(x) < 1) return x * 100;
    return x;
  };

  const toNumberList = (arr) => (Array.isArray(arr) ? arr.map((v) => Number(v ?? 0)) : []);
  const toStringList = (arr) => (Array.isArray(arr) ? arr.map((v) => String(v ?? '')) : []);

  const winRate = firstNum(['win_rate', 'winRate']);
  const avgRoiRaw = firstNum(['avg_roi', 'avgRoi', 'roi']);
  const avgRoi = Number.isFinite(avgRoiRaw) ? toRatioAsPercent(avgRoiRaw) : NaN;
  const avgDurationDays = firstNum(['avg_duration_in_days', 'avgHoldDays', 'avg_duration_days']);

  const annualRaw = firstNum(['annual_return', 'annualReturn']);
  const annualReturn = Number.isFinite(annualRaw) ? toRatioAsPercent(annualRaw) : NaN;

  const totalInvestments = firstNum(['total_investments', 'totalInvestments']);
  const totalOpenInvestments = firstNum(['total_open_investments', 'totalOpenInvestments']);
  const totalWinInvestments = firstNum(['total_win_investments', 'totalWinInvestments']);
  const totalLossInvestments = firstNum(['total_loss_investments', 'totalLossInvestments']);
  const stocksWithOpportunities = firstNum(['stocks_have_opportunities', 'stocksWithOpportunities']);
  const avgInvestmentsPerStock = firstNum(['avg_investments_per_stock', 'avgInvestmentsPerStock']);
  const avgProfitPerInvestment = firstNum(['avg_profit_per_investment', 'avgProfitPerInvestment']);
  const avgProfitPerStock = firstNum(['avg_profit_per_stock', 'avgProfitPerStock']);

  const roiPctLabelsIn = toStringList(
    m.roiPercentileLabels || m.roi_percentile_labels,
  );
  const roiPctValuesRaw = toNumberList(
    m.roiPercentileValues || m.roi_percentile_values,
  );
  const pv = roiPctValuesRaw.length >= 9 ? roiPctValuesRaw.slice(0, 9) : [];
  const defaultPctLabels = ['10%分位', '20%分位', '30%分位', '40%分位', '50%分位', '60%分位', '70%分位', '80%分位', '90%分位'];
  const labelsForChart = pv.length === 9 && roiPctLabelsIn.length === 9
    ? roiPctLabelsIn
    : defaultPctLabels;

  let roiP10 = firstNum(['roiP10', 'roi_p10']);
  let roiP20 = firstNum(['roiP20', 'roi_p20']);
  let roiP30 = firstNum(['roiP30', 'roi_p30']);
  let roiP40 = firstNum(['roiP40', 'roi_p40']);
  let roiP50 = firstNum(['roiP50', 'roi_p50']);
  let roiP60 = firstNum(['roiP60', 'roi_p60']);
  let roiP70 = firstNum(['roiP70', 'roi_p70']);
  let roiP80 = firstNum(['roiP80', 'roi_p80']);
  let roiP90 = firstNum(['roiP90', 'roi_p90']);
  let roiP25 = firstNum(['roiP25', 'roi_p25']);
  let roiP75 = firstNum(['roiP75', 'roi_p75']);
  let roiIqr = firstNum(['roiIqr', 'roi_iqr']);
  if (pv.length === 9 && pv.every((x) => Number.isFinite(x))) {
    [roiP10, roiP20, roiP30, roiP40, roiP50, roiP60, roiP70, roiP80, roiP90] = pv;
    if (!Number.isFinite(roiP25)) roiP25 = Number(((pv[1] + pv[2]) / 2).toFixed(2));
    if (!Number.isFinite(roiP50)) roiP50 = Number(pv[4].toFixed(2));
    if (!Number.isFinite(roiP75)) roiP75 = Number(((pv[6] + pv[7]) / 2).toFixed(2));
    if (!Number.isFinite(roiIqr) && Number.isFinite(roiP25) && Number.isFinite(roiP75)) {
      roiIqr = Number((roiP75 - roiP25).toFixed(2));
    }
  }
  const roiConclusion = String(m.roiConclusion || m.roi_conclusion || '').trim();

  const roiStdPct = firstNum(['roiStdPct', 'roi_std_pct']);

  const roiBucketLabels = toStringList(m.roiBucketLabels || m.roi_bucket_labels);
  const roiBucketCounts = toNumberList(m.roiBucketCounts || m.roi_bucket_counts);
  const roiBucketBinCount = Number(m.roiBucketBinCount ?? m.roi_bucket_bin_count ?? 0);

  const hasCoreSummary = [winRate, avgRoi, avgDurationDays, annualReturn].every((x) => Number.isFinite(x));
  const hasAny = hasCoreSummary
    || (Number.isFinite(totalInvestments) && totalInvestments > 0)
    || [m.win_rate, m.winRate, m.total_investments].some((v) => v !== undefined && v !== null);

  if (!hasAny) return null;

  const overviewOk = hasCoreSummary;
  const sampleCoverageOk = [totalInvestments, stocksWithOpportunities, avgInvestmentsPerStock, totalOpenInvestments]
    .every((x) => Number.isFinite(x));
  const profitBasicsOk = [totalWinInvestments, totalLossInvestments, avgProfitPerInvestment, avgProfitPerStock]
    .every((x) => Number.isFinite(x));

  const roiPercentileVizOk = pv.length === 9 && pv.every((x) => Number.isFinite(x));
  const roiBucketVizOk = roiBucketLabels.length > 0
    && roiBucketCounts.length === roiBucketLabels.length;

  return {
    winRate: Number.isFinite(winRate) ? Number(winRate.toFixed(1)) : NaN,
    avgRoi: Number.isFinite(avgRoi) ? Number(avgRoi.toFixed(2)) : NaN,
    avgDurationDays: Number.isFinite(avgDurationDays) ? Number(avgDurationDays.toFixed(1)) : NaN,
    annualReturn: Number.isFinite(annualReturn) ? Number(annualReturn.toFixed(2)) : NaN,
    totalInvestments: Number.isFinite(totalInvestments) ? Math.round(totalInvestments) : 0,
    totalOpenInvestments: Number.isFinite(totalOpenInvestments) ? Math.round(totalOpenInvestments) : 0,
    totalWinInvestments: Number.isFinite(totalWinInvestments) ? Math.round(totalWinInvestments) : 0,
    totalLossInvestments: Number.isFinite(totalLossInvestments) ? Math.round(totalLossInvestments) : 0,
    stocksWithOpportunities: Number.isFinite(stocksWithOpportunities) ? Math.round(stocksWithOpportunities) : 0,
    avgInvestmentsPerStock: Number.isFinite(avgInvestmentsPerStock) ? Number(avgInvestmentsPerStock.toFixed(2)) : NaN,
    avgProfitPerInvestment: Number.isFinite(avgProfitPerInvestment)
      ? Number(avgProfitPerInvestment.toFixed(2))
      : NaN,
    avgProfitPerStock: Number.isFinite(avgProfitPerStock) ? Number(avgProfitPerStock.toFixed(2)) : NaN,
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
    roiStdPct,
    roiConclusion,
    roiBucketLabels,
    roiBucketCounts,
    roiBucketBinCount: Number.isFinite(roiBucketBinCount) && roiBucketBinCount > 0
      ? Math.round(roiBucketBinCount)
      : 0,
    roiPercentileLabels: labelsForChart,
    roiPercentileValues: pv,
    _availability: {
      overview: overviewOk,
      sampleCoverage: sampleCoverageOk,
      profitBasics: profitBasicsOk,
      roiPercentileViz: roiPercentileVizOk,
      roiBucketViz: roiBucketVizOk,
    },
  };
}

export function buildPriceMetrics(executionState) {
  return normalizePriceMetricsFromSummary(executionState?.result?.price);
}

export function buildCapitalMetricsFromBase(base) {
  if (!base) return null;
  const initialCapital = Number(base.initialCapital ?? 1_000_000);
  const totalReturnPct = Number(
    base.totalReturnPct
      ?? (base.totalReturn !== undefined ? Number(base.totalReturn) * 100 : 0),
  );
  const maxDrawdownPct = Number(
    base.maxDrawdownPct
      ?? (base.maxDrawdown !== undefined ? Number(base.maxDrawdown) * 100 : 0),
  );
  const winRatePct = Number(
    base.winRatePct
      ?? (base.winRate !== undefined ? Number(base.winRate) * 100 : 0),
  );

  const finalEquity = Number(base.finalEquity ?? Math.round(initialCapital * (1 + totalReturnPct / 100)));
  const totalProfit = Number(base.totalProfit ?? (finalEquity - initialCapital));
  const calmarRatio = maxDrawdownPct > 0 ? Number((totalReturnPct / maxDrawdownPct).toFixed(2)) : 0;

  const derivedSellTrades = Math.max(80, Math.round(140 + winRatePct * 1.1));
  const sellTrades = Number(base.sellTrades ?? derivedSellTrades);
  const buyTrades = Number(base.buyTrades ?? sellTrades);
  const totalTrades = Number(base.totalTrades ?? (buyTrades + sellTrades));
  const winTrades = Number(base.winTrades ?? Math.round(sellTrades * (winRatePct / 100)));
  const lossTrades = Number(base.lossTrades ?? Math.max(0, sellTrades - winTrades));
  const avgPnlPerTrade = Number(base.avgPnlPerTrade ?? (sellTrades > 0 ? Math.round(totalProfit / sellTrades) : 0));

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

/**
 * ``result_report.capital_allocation`` 槽位（``CapitalReport.to_dict()`` + BFF 图表字段，snake_case / camelCase）
 */
export function normalizeCapitalMetricsFromSummary(slot) {
  if (!slot || typeof slot !== 'object') return null;

  const m = { ...slot };

  const firstNum = (keys) => {
    for (const k of keys) {
      if (m[k] === undefined || m[k] === null) continue;
      const n = Number(m[k]);
      if (Number.isFinite(n)) return n;
    }
    return NaN;
  };

  const ratioToPct = (v) => {
    const x = Number(v);
    if (!Number.isFinite(x)) return NaN;
    if (Math.abs(x) <= 1.0001) return x * 100;
    return x;
  };

  const toStrList = (arr) => (Array.isArray(arr) ? arr.map((v) => String(v ?? '')) : []);
  const toNumList = (arr) => (Array.isArray(arr) ? arr.map((v) => Number(v ?? 0)) : []);

  const equityCurveLabels = toStrList(m.equityCurveLabels || m.equity_curve_labels);
  const equityCurveValues = toNumList(m.equityCurveValues || m.equity_curve_values);

  let initialCapital = firstNum(['initialCapital', 'initial_capital']);
  let finalEquity = firstNum(['finalEquity', 'final_total_equity', 'final_equity', 'endCapital']);
  if (!Number.isFinite(initialCapital) && equityCurveValues.length > 0) {
    initialCapital = equityCurveValues[0];
  }
  if (!Number.isFinite(finalEquity) && equityCurveValues.length > 0) {
    finalEquity = equityCurveValues[equityCurveValues.length - 1];
  }

  let totalReturnPct = firstNum(['totalReturnPct', 'total_return_pct']);
  if (!Number.isFinite(totalReturnPct)) {
    const tr = firstNum(['total_return', 'totalReturn']);
    if (Number.isFinite(tr)) totalReturnPct = ratioToPct(tr);
  }
  if (!Number.isFinite(totalReturnPct)) {
    const rp = firstNum(['retPct', 'return_pct', 'ret_pct']);
    if (Number.isFinite(rp)) totalReturnPct = ratioToPct(rp);
  }
  if (!Number.isFinite(totalReturnPct) && Number.isFinite(initialCapital) && initialCapital > 1e-9
    && Number.isFinite(finalEquity)) {
    totalReturnPct = ((finalEquity - initialCapital) / initialCapital) * 100;
  }

  let maxDrawdownPct = firstNum(['maxDrawdownPct', 'max_drawdown_pct']);
  if (!Number.isFinite(maxDrawdownPct)) {
    const md = firstNum(['max_drawdown', 'maxDrawdown']);
    if (Number.isFinite(md)) maxDrawdownPct = ratioToPct(md);
  }

  let winRatePct = firstNum(['winRatePct', 'win_rate_pct']);
  if (!Number.isFinite(winRatePct)) {
    const wr = firstNum(['win_rate', 'winRate']);
    if (Number.isFinite(wr)) winRatePct = ratioToPct(wr);
  }

  const totalProfitRaw = firstNum(['totalProfit', 'total_profit', 'profit']);
  const totalTrades = firstNum(['total_trades', 'totalTrades']);
  const buyTrades = firstNum(['buy_trades', 'buyTrades']);
  const sellTrades = firstNum(['sell_trades', 'sellTrades']);
  const winTrades = firstNum(['win_trades', 'winTrades']);
  const lossTrades = firstNum(['loss_trades', 'lossTrades']);
  const avgPnlPerTrade = firstNum(['avg_pnl_per_trade', 'avgPnlPerTrade']);

  const calmarRatio = firstNum(['calmarRatio', 'calmar_ratio']);

  let drawdownCurveValues = toNumList(m.drawdownCurveValues || m.drawdown_curve_values);

  const avgOpenPositions = firstNum(['avgOpenPositions', 'average_open_positions']);
  const peakPositions = firstNum(['peakPositions', 'peak_open_positions']);
  const fullExposureDaysRatio = firstNum(['fullExposureDaysRatio', 'full_exposure_days_ratio_pct']);
  const avgCashRatio = firstNum(['avgCashRatio', 'average_cash_ratio_pct']);
  const capitalUtilizationRatio = firstNum(['capitalUtilizationRatio', 'capital_utilization_ratio_pct']);

  const maxLossStreak = firstNum(['maxLossStreak', 'max_consecutive_losing_sells']);
  const maxDrawdownDurationDays = firstNum(['maxDrawdownDurationDays', 'max_drawdown_duration_days']);

  let worstTradePnls = toNumList(m.worstTradePnls || m.worst_sell_pnls);
  while (worstTradePnls.length < 3) worstTradePnls.push(0);

  const stockCount = firstNum(['stockCount', 'stock_count']);
  const avgTradesPerStock = firstNum(['avgTradesPerStock', 'average_trades_per_stock']);
  const top5ContributionRatio = firstNum(['top5ContributionRatio', 'top5_profit_concentration_pct']);
  const stockPnlCv = firstNum(['stockPnlCv', 'stock_profit_coefficient_of_variation']);

  const hasCore = Number.isFinite(initialCapital) && Number.isFinite(finalEquity);
  const hasCharts = equityCurveLabels.length > 0 && equityCurveValues.length === equityCurveLabels.length;
  const hasAny = hasCore || hasCharts;

  if (!hasAny) return null;

  const fillFromDerived = !hasCharts && hasCore;
  const derivedBase = fillFromDerived
    ? buildCapitalMetricsFromBase({
      initialCapital,
      totalReturnPct: Number.isFinite(totalReturnPct) ? totalReturnPct : 0,
      maxDrawdownPct: Number.isFinite(maxDrawdownPct) ? maxDrawdownPct : 0,
      winRatePct: Number.isFinite(winRatePct) ? winRatePct : 0,
      totalProfit: Number.isFinite(totalProfitRaw) ? totalProfitRaw : (finalEquity - initialCapital),
      sellTrades,
      buyTrades,
      totalTrades,
      winTrades,
      lossTrades,
      avgPnlPerTrade,
      finalEquity,
    })
    : null;

  let ddOut = drawdownCurveValues;
  if (hasCharts && ddOut.length !== equityCurveLabels.length) {
    const vs = equityCurveValues;
    let peak = vs[0] ?? 0;
    ddOut = vs.map((v) => {
      peak = Math.max(peak, v);
      return peak > 1e-12 ? Number((((peak - v) / peak) * 100).toFixed(2)) : 0;
    });
  } else if (!hasCharts) {
    ddOut = derivedBase?.drawdownCurveValues ?? [];
  }

  const totalProfit = Number.isFinite(totalProfitRaw)
    ? totalProfitRaw
    : (derivedBase?.totalProfit ?? (finalEquity - initialCapital));

  return {
    initialCapital,
    finalEquity: Number.isFinite(finalEquity) ? finalEquity : (derivedBase?.finalEquity ?? 0),
    totalProfit,
    totalReturnPct: Number.isFinite(totalReturnPct)
      ? Number(totalReturnPct.toFixed(2))
      : (derivedBase?.totalReturnPct ?? 0),
    maxDrawdownPct: Number.isFinite(maxDrawdownPct)
      ? Number(maxDrawdownPct.toFixed(2))
      : (derivedBase?.maxDrawdownPct ?? 0),
    calmarRatio: Number.isFinite(calmarRatio) ? calmarRatio : (derivedBase?.calmarRatio ?? 0),
    totalTrades: Number.isFinite(totalTrades) ? Math.round(totalTrades) : (derivedBase?.totalTrades ?? 0),
    buyTrades: Number.isFinite(buyTrades) ? Math.round(buyTrades) : (derivedBase?.buyTrades ?? 0),
    sellTrades: Number.isFinite(sellTrades) ? Math.round(sellTrades) : (derivedBase?.sellTrades ?? 0),
    winTrades: Number.isFinite(winTrades) ? Math.round(winTrades) : (derivedBase?.winTrades ?? 0),
    lossTrades: Number.isFinite(lossTrades) ? Math.round(lossTrades) : (derivedBase?.lossTrades ?? 0),
    winRatePct: Number.isFinite(winRatePct) ? Number(winRatePct.toFixed(2)) : (derivedBase?.winRatePct ?? 0),
    avgPnlPerTrade: Number.isFinite(avgPnlPerTrade)
      ? Math.round(avgPnlPerTrade)
      : (derivedBase?.avgPnlPerTrade ?? 0),
    avgOpenPositions: Number.isFinite(avgOpenPositions)
      ? Number(avgOpenPositions.toFixed(1))
      : (derivedBase?.avgOpenPositions ?? 0),
    peakPositions: Number.isFinite(peakPositions)
      ? Math.round(peakPositions)
      : (derivedBase?.peakPositions ?? 0),
    fullExposureDaysRatio: Number.isFinite(fullExposureDaysRatio)
      ? Number(fullExposureDaysRatio.toFixed(1))
      : (derivedBase?.fullExposureDaysRatio ?? 0),
    avgCashRatio: Number.isFinite(avgCashRatio)
      ? Number(avgCashRatio.toFixed(1))
      : (derivedBase?.avgCashRatio ?? 0),
    capitalUtilizationRatio: Number.isFinite(capitalUtilizationRatio)
      ? Number(capitalUtilizationRatio.toFixed(1))
      : (derivedBase?.capitalUtilizationRatio ?? 0),
    maxLossStreak: Number.isFinite(maxLossStreak)
      ? Math.round(maxLossStreak)
      : (derivedBase?.maxLossStreak ?? 0),
    maxDrawdownDurationDays: Number.isFinite(maxDrawdownDurationDays)
      ? Math.round(maxDrawdownDurationDays)
      : (derivedBase?.maxDrawdownDurationDays ?? 0),
    worstTradePnls: worstTradePnls.slice(0, 3),
    stockCount: Number.isFinite(stockCount)
      ? Math.round(stockCount)
      : (derivedBase?.stockCount ?? 0),
    avgTradesPerStock: Number.isFinite(avgTradesPerStock)
      ? Number(avgTradesPerStock.toFixed(2))
      : (derivedBase?.avgTradesPerStock ?? 0),
    top5ContributionRatio: Number.isFinite(top5ContributionRatio)
      ? Number(top5ContributionRatio.toFixed(1))
      : (derivedBase?.top5ContributionRatio ?? 0),
    stockPnlCv: Number.isFinite(stockPnlCv)
      ? Number(stockPnlCv.toFixed(2))
      : (derivedBase?.stockPnlCv ?? 0),
    equityCurveLabels: hasCharts ? equityCurveLabels : (derivedBase?.equityCurveLabels ?? []),
    equityCurveValues: hasCharts ? equityCurveValues : (derivedBase?.equityCurveValues ?? []),
    drawdownCurveValues: hasCharts ? ddOut : (derivedBase?.drawdownCurveValues ?? []),
  };
}

export function buildCapitalMetrics(executionState) {
  const fromSlot = normalizeCapitalMetricsFromSummary(executionState?.result?.capital_allocation);
  if (fromSlot) return fromSlot;

  const summary = executionState?.result?.capital;
  const parsed = summary
    ? {
      ...summary,
      totalReturnPct: summary.totalReturnPct !== undefined
        ? Number(summary.totalReturnPct)
        : Number((Number(summary.totalReturn || 0) * 100).toFixed(2)),
      maxDrawdownPct: summary.maxDrawdownPct !== undefined
        ? Number(summary.maxDrawdownPct)
        : Number((Number(summary.maxDrawdown || 0) * 100).toFixed(2)),
      winRatePct: summary.winRatePct !== undefined
        ? Number(summary.winRatePct)
        : Number((Number(summary.winRate || 0) * 100).toFixed(2)),
    }
    : null;
  const hasRealCapitalMetrics = Boolean(
    parsed && Object.keys(parsed).length > 0,
  );
  const base = hasRealCapitalMetrics ? parsed : MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION.latest;
  return buildCapitalMetricsFromBase(base);
}
