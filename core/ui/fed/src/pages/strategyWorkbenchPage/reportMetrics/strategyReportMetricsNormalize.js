/**
 * 策略报告 metrics：仅认 BFF V2-07 / 快照槽位当前形态，不做字段别名与推导补全。
 *
 * - enum：``{ enumMetrics: { … } }``（``EnumeratorReport.to_bff_payload``，camelCase）
 * - price：``PriceReport.to_dict()`` 扁平 snake_case
 * - capital：``CapitalReport`` + BFF 扩展，snake_case
 */

export const REPORT_BLOCK_UNAVAILABLE_ZH = '数据异常，无法显示该结果。';

function readEnumMetrics(slot) {
  if (!slot || typeof slot !== 'object') return null;
  const inner = slot.enumMetrics;
  return inner && typeof inner === 'object' ? inner : null;
}

function numOrNaN(raw) {
  if (raw === undefined || raw === null || raw === '') return NaN;
  const n = Number(raw);
  return Number.isFinite(n) ? n : NaN;
}

function toNumberList(arr) {
  return Array.isArray(arr) ? arr.map((v) => Number(v ?? 0)) : [];
}

function toStringList(arr) {
  return Array.isArray(arr) ? arr.map((v) => String(v ?? '')) : [];
}

/**
 * ``result_report.enum`` 槽位 → FED 展示结构；缺字段则对应块 ``_availability`` 为 false。
 */
export function normalizeEnumMetricsFromSummary(slot) {
  const m = readEnumMetrics(slot);
  if (!m) return null;

  const totalOpportunities = numOrNaN(m.totalOpportunities);
  const totalStocks = numOrNaN(m.totalStocks);
  const triggerStocks = numOrNaN(m.triggerStocks);
  const triggerRatio = numOrNaN(m.triggerRatio);
  const avgPerStock = numOrNaN(m.avgPerStock);
  const completedRatio = numOrNaN(m.completedRatio);
  const completedCount = numOrNaN(m.completedCount);
  const unfinishedCount = numOrNaN(m.unfinishedCount);

  const opportunityCountLabels = toStringList(m.opportunityCountLabels);
  const opportunityCountStockCounts = toNumberList(m.opportunityCountStockCounts);
  const opportunityCountStockRatios = toNumberList(m.opportunityCountStockRatios);
  const opportunityCountMin = numOrNaN(m.opportunityCountMin);
  const opportunityCountMax = numOrNaN(m.opportunityCountMax);
  const opportunityCountBucketCount = numOrNaN(m.opportunityCountBucketCount);

  const meanGap = numOrNaN(m.meanGap);
  const meanDuration = numOrNaN(m.meanDuration);
  const stdGap = numOrNaN(m.stdGap);
  const cv = numOrNaN(m.cv);
  const dispersionConclusion = String(m.dispersionConclusion ?? '');

  const percentileLabels = toStringList(m.percentileLabels);
  const percentileValues = toNumberList(m.percentileValues);

  const overviewOk = Number.isFinite(totalOpportunities)
    && Number.isFinite(totalStocks)
    && totalStocks > 0
    && totalOpportunities >= 0
    && Number.isFinite(triggerStocks)
    && Number.isFinite(triggerRatio)
    && Number.isFinite(avgPerStock)
    && Number.isFinite(completedRatio)
    && Number.isFinite(completedCount);

  const distributionOk = opportunityCountLabels.length > 0
    && opportunityCountStockCounts.length === opportunityCountLabels.length
    && opportunityCountStockRatios.length === opportunityCountLabels.length;

  const timingOk = Number.isFinite(meanGap) && Number.isFinite(meanDuration);

  if (!overviewOk && !distributionOk && !timingOk) {
    return null;
  }

  return {
    totalOpportunities,
    totalStocks,
    triggerStocks,
    triggerRatio,
    avgPerStock,
    completedRatio,
    completedCount,
    unfinishedCount,
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
      stockStats: overviewOk,
      distribution: distributionOk,
      timing: timingOk,
    },
  };
}

/** ``result_report.price_factor``：``PriceReport.to_dict()`` 扁平 snake_case。 */
export function normalizePriceMetricsFromSummary(slot) {
  if (!slot || typeof slot !== 'object') return null;

  const num = (key) => numOrNaN(slot[key]);

  const winRate = num('win_rate');
  const avgRoiRaw = num('avg_roi');
  const avgRoi = Number.isFinite(avgRoiRaw) && Math.abs(avgRoiRaw) < 1 ? avgRoiRaw * 100 : avgRoiRaw;
  const avgDurationDays = num('avg_duration_in_days');
  const annualRaw = num('annual_return');
  const annualReturn = Number.isFinite(annualRaw) && Math.abs(annualRaw) < 1 ? annualRaw * 100 : annualRaw;

  const totalInvestments = num('total_investments');
  const totalOpenInvestments = num('total_open_investments');
  const totalWinInvestments = num('total_win_investments');
  const totalLossInvestments = num('total_loss_investments');
  const stocksWithOpportunities = num('stocks_have_opportunities');
  const avgInvestmentsPerStock = num('avg_investments_per_stock');
  const avgProfitPerInvestment = num('avg_profit_per_investment');
  const avgProfitPerStock = num('avg_profit_per_stock');

  const roiPctLabelsIn = toStringList(slot.roi_percentile_labels);
  const roiPctValuesRaw = toNumberList(slot.roi_percentile_values);
  const pv = roiPctValuesRaw.length >= 9 ? roiPctValuesRaw.slice(0, 9) : [];

  const roiP10 = num('roi_p10');
  const roiP20 = num('roi_p20');
  const roiP30 = num('roi_p30');
  const roiP40 = num('roi_p40');
  const roiP50 = num('roi_p50');
  const roiP60 = num('roi_p60');
  const roiP70 = num('roi_p70');
  const roiP80 = num('roi_p80');
  const roiP90 = num('roi_p90');
  const roiP25 = num('roi_p25');
  const roiP75 = num('roi_p75');
  const roiIqr = num('roi_iqr');
  const roiConclusion = String(slot.roi_conclusion ?? '').trim();
  const roiStdPct = num('roi_std_pct');

  const roiBucketLabels = toStringList(slot.roi_bucket_labels);
  const roiBucketCounts = toNumberList(slot.roi_bucket_counts);
  const roiBucketBinCount = num('roi_bucket_bin_count');

  const overviewOk = [winRate, avgRoi, avgDurationDays, annualReturn].every((x) => Number.isFinite(x));
  const sampleCoverageOk = [totalInvestments, stocksWithOpportunities, avgInvestmentsPerStock, totalOpenInvestments]
    .every((x) => Number.isFinite(x));
  const profitBasicsOk = [totalWinInvestments, totalLossInvestments, avgProfitPerInvestment, avgProfitPerStock]
    .every((x) => Number.isFinite(x));
  const roiPercentileVizOk = pv.length === 9 && pv.every((x) => Number.isFinite(x));
  const roiBucketVizOk = roiBucketLabels.length > 0
    && roiBucketCounts.length === roiBucketLabels.length;

  if (!overviewOk && !sampleCoverageOk && !profitBasicsOk) {
    return null;
  }

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
    roiBucketBinCount: Number.isFinite(roiBucketBinCount) ? Math.round(roiBucketBinCount) : 0,
    roiPercentileLabels: roiPctLabelsIn.length === 9 ? roiPctLabelsIn : [],
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

/** ``result_report.capital_allocation``：snake_case，含 ``equity_curve_*``。 */
export function normalizeCapitalMetricsFromSummary(slot) {
  if (!slot || typeof slot !== 'object') return null;

  const num = (key) => numOrNaN(slot[key]);

  const equityCurveLabels = Array.isArray(slot.equity_curve_labels)
    ? slot.equity_curve_labels.map((v) => String(v ?? ''))
    : [];
  const equityCurveValues = Array.isArray(slot.equity_curve_values)
    ? slot.equity_curve_values.map((v) => Number(v ?? 0))
    : [];

  const initialCapital = num('initial_capital');
  const finalEquity = num('final_total_equity');
  const totalReturnPct = (() => {
    const x = num('total_return');
    return Number.isFinite(x) && Math.abs(x) <= 1 ? x * 100 : x;
  })();
  const maxDrawdownPct = (() => {
    const x = num('max_drawdown');
    return Number.isFinite(x) && Math.abs(x) <= 1 ? x * 100 : x;
  })();
  const winRatePct = (() => {
    const x = num('win_rate');
    return Number.isFinite(x) && Math.abs(x) <= 1 ? x * 100 : x;
  })();
  const totalProfit = num('total_profit');
  const totalTrades = num('total_trades');
  const buyTrades = num('buy_trades');
  const sellTrades = num('sell_trades');
  const winTrades = num('win_trades');
  const lossTrades = num('loss_trades');
  const avgPnlPerTrade = num('avg_pnl_per_trade');

  const hasCharts = equityCurveLabels.length >= 2
    && equityCurveValues.length === equityCurveLabels.length
    && equityCurveValues.every((v) => Number.isFinite(v));

  const required = [
    initialCapital, finalEquity, totalReturnPct, maxDrawdownPct, winRatePct,
    totalProfit, totalTrades, buyTrades, sellTrades, winTrades, lossTrades, avgPnlPerTrade,
  ];
  if (!required.every((x) => Number.isFinite(x)) || !hasCharts) {
    return null;
  }

  const calmarRatio = num('calmar_ratio');
  const drawdownCurveValues = Array.isArray(slot.drawdown_curve_values)
    ? slot.drawdown_curve_values.map((v) => Number(v ?? 0))
    : [];
  const worstTradePnls = Array.isArray(slot.worst_sell_pnls)
    ? slot.worst_sell_pnls.map((v) => Number(v ?? 0))
    : [];

  const stockSummary = slot.stock_summary && typeof slot.stock_summary === 'object'
    ? slot.stock_summary
    : {};
  const stockCount = Object.keys(stockSummary).length;

  return {
    initialCapital,
    finalEquity,
    totalProfit,
    totalReturnPct: Number(totalReturnPct.toFixed(2)),
    maxDrawdownPct: Number(maxDrawdownPct.toFixed(2)),
    calmarRatio: Number.isFinite(calmarRatio) ? Number(calmarRatio.toFixed(4)) : NaN,
    totalTrades: Math.round(totalTrades),
    buyTrades: Math.round(buyTrades),
    sellTrades: Math.round(sellTrades),
    winTrades: Math.round(winTrades),
    lossTrades: Math.round(lossTrades),
    winRatePct: Number(winRatePct.toFixed(2)),
    avgPnlPerTrade: Math.round(avgPnlPerTrade),
    avgOpenPositions: num('average_open_positions'),
    peakPositions: num('peak_open_positions'),
    fullExposureDaysRatio: num('full_exposure_days_ratio_pct'),
    avgCashRatio: num('average_cash_ratio_pct'),
    capitalUtilizationRatio: num('capital_utilization_ratio_pct'),
    maxLossStreak: num('max_consecutive_losing_sells'),
    maxDrawdownDurationDays: num('max_drawdown_duration_days'),
    worstTradePnls: worstTradePnls.slice(0, 3),
    stockCount,
    avgTradesPerStock: num('average_trades_per_stock'),
    top5ContributionRatio: num('top5_profit_concentration_pct'),
    stockPnlCv: num('stock_profit_coefficient_of_variation'),
    equityCurveLabels,
    equityCurveValues,
    drawdownCurveValues,
  };
}
