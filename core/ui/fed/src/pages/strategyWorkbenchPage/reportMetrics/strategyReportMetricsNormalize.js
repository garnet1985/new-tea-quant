/**
 * 策略报告 metrics：API/BFF 快照字段 → 面板展示用结构。
 * **枚举/资金**仅以 BFF snake_case 槽位为准，不合成占位数据；无完整字段时返回 ``null``（见各 ``normalize*`` 注释）。
 */

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
  if (!Number.isFinite(completedRatio)) {
    const alt = normalizePercent(pick('completionRate', 'completion_rate'));
    if (Number.isFinite(alt)) completedRatio = alt;
  }

  let completedCount = Number(pick('completedCount', 'completed_count'));
  if (
    !Number.isFinite(completedCount)
    && Number.isFinite(completedRatio)
    && Number.isFinite(totalOpportunities)
  ) {
    completedCount = Math.round((completedRatio / 100) * totalOpportunities);
  }

  if (!Number.isFinite(completedRatio)) completedRatio = 0;
  if (!Number.isFinite(completedCount)) completedCount = 0;

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
    && totalOpportunities >= 0;

  const stockStatsOk = Number.isFinite(totalStocks)
    && totalStocks > 0
    && Number.isFinite(triggerStocks)
    && Number.isFinite(avgPerStock);

  const distributionOk = opportunityCountLabels.length > 0
    && opportunityCountStockCounts.length === opportunityCountLabels.length
    && opportunityCountStockRatios.length === opportunityCountLabels.length;

  const timingOk = [meanGap, meanDuration].every((x) => Number.isFinite(Number(x)));

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

/**
 * ``result_report.capital_allocation``（``CapitalReport.to_dict()`` + ``_merge_bff_ui_extensions``，仅 snake_case）。
 *
 * 必填（缺任一则返回 null，请清工作台/模拟缓存后重跑资金步）：
 * - initial_capital, final_total_equity, total_return, max_drawdown, win_rate（0~1 比例）
 * - total_profit, total_trades, buy_trades, sell_trades, win_trades, loss_trades, avg_pnl_per_trade
 * - equity_curve_labels, equity_curve_values（等长且 length >= 2）
 */
export function normalizeCapitalMetricsFromSummary(slot) {
  if (!slot || typeof slot !== 'object') return null;

  const num = (key) => {
    const v = slot[key];
    if (v === undefined || v === null) return NaN;
    const n = Number(v);
    return Number.isFinite(n) ? n : NaN;
  };

  const ratioToPct = (v) => {
    const x = Number(v);
    if (!Number.isFinite(x)) return NaN;
    if (Math.abs(x) <= 1.0001) return x * 100;
    return x;
  };

  const equityCurveLabels = Array.isArray(slot.equity_curve_labels)
    ? slot.equity_curve_labels.map((v) => String(v ?? ''))
    : [];
  const equityCurveValues = Array.isArray(slot.equity_curve_values)
    ? slot.equity_curve_values.map((v) => Number(v ?? 0))
    : [];

  const initialCapital = num('initial_capital');
  const finalEquity = num('final_total_equity');
  const totalReturnPct = ratioToPct(slot.total_return);
  const maxDrawdownPct = ratioToPct(slot.max_drawdown);
  const winRatePct = ratioToPct(slot.win_rate);
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

  let calmarRatio = num('calmar_ratio');
  if (!Number.isFinite(calmarRatio) && maxDrawdownPct > 1e-9) {
    calmarRatio = totalReturnPct / maxDrawdownPct;
  }

  let drawdownCurveValues = Array.isArray(slot.drawdown_curve_values)
    ? slot.drawdown_curve_values.map((v) => Number(v ?? 0))
    : [];
  if (drawdownCurveValues.length !== equityCurveLabels.length) {
    let peak = equityCurveValues[0] ?? 0;
    drawdownCurveValues = equityCurveValues.map((v) => {
      peak = Math.max(peak, v);
      return peak > 1e-12 ? Number((((peak - v) / peak) * 100).toFixed(2)) : 0;
    });
  }

  let worstTradePnls = Array.isArray(slot.worst_sell_pnls)
    ? slot.worst_sell_pnls.map((v) => Number(v ?? 0))
    : [];
  while (worstTradePnls.length < 3) worstTradePnls.push(0);

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
    calmarRatio: Number.isFinite(calmarRatio) ? Number(calmarRatio.toFixed(4)) : 0,
    totalTrades: Math.round(totalTrades),
    buyTrades: Math.round(buyTrades),
    sellTrades: Math.round(sellTrades),
    winTrades: Math.round(winTrades),
    lossTrades: Math.round(lossTrades),
    winRatePct: Number(winRatePct.toFixed(2)),
    avgPnlPerTrade: Math.round(avgPnlPerTrade),
    avgOpenPositions: (() => {
      const v = num('average_open_positions');
      return Number.isFinite(v) ? Number(v.toFixed(1)) : 0;
    })(),
    peakPositions: (() => {
      const v = num('peak_open_positions');
      return Number.isFinite(v) ? Math.round(v) : 0;
    })(),
    fullExposureDaysRatio: (() => {
      const v = num('full_exposure_days_ratio_pct');
      return Number.isFinite(v) ? Number(v.toFixed(1)) : 0;
    })(),
    avgCashRatio: (() => {
      const v = num('average_cash_ratio_pct');
      return Number.isFinite(v) ? Number(v.toFixed(1)) : 0;
    })(),
    capitalUtilizationRatio: (() => {
      const v = num('capital_utilization_ratio_pct');
      return Number.isFinite(v) ? Number(v.toFixed(1)) : 0;
    })(),
    maxLossStreak: (() => {
      const v = num('max_consecutive_losing_sells');
      return Number.isFinite(v) ? Math.round(v) : 0;
    })(),
    maxDrawdownDurationDays: (() => {
      const v = num('max_drawdown_duration_days');
      return Number.isFinite(v) ? Math.round(v) : 0;
    })(),
    worstTradePnls: worstTradePnls.slice(0, 3),
    stockCount,
    avgTradesPerStock: (() => {
      if (stockCount > 0) return Number((sellTrades / stockCount).toFixed(2));
      const v = num('average_trades_per_stock');
      return Number.isFinite(v) ? Number(v.toFixed(2)) : 0;
    })(),
    top5ContributionRatio: (() => {
      const v = num('top5_profit_concentration_pct');
      return Number.isFinite(v) ? Number(v.toFixed(1)) : 0;
    })(),
    stockPnlCv: (() => {
      const v = num('stock_profit_coefficient_of_variation');
      return Number.isFinite(v) ? Number(v.toFixed(2)) : 0;
    })(),
    equityCurveLabels,
    equityCurveValues,
    drawdownCurveValues,
  };
}
