/**
 * 报告页「样本股票」表格行生成（Story / 本地调试）；主界面逐股表仅在接口返回行数据时展示，不再调用此处。
 */
import { SAMPLE_STOCK_CODES, SAMPLE_STOCK_DISPLAY_NAMES } from './strategyWorkbenchMocks';

export function buildPriceSampleStockRows(metrics) {
  const baseCount = Math.max(10, Math.min(18, metrics.totalInvestments));
  return Array.from({ length: baseCount }).map((_, index) => {
    const seed = index + 1;
    const winRate = Math.max(20, Math.min(92, Number((metrics.winRate + (seed % 5) * 4 - 8).toFixed(1))));
    const roi = Number((metrics.avgRoi + (seed % 7) * 2.3 - 6.9).toFixed(1));
    const holdDays = Math.max(3, Math.round(metrics.avgDurationDays + (seed % 6) * 3 - 7));
    return {
      id: `${SAMPLE_STOCK_CODES[index]}-${seed}`,
      stockCode: SAMPLE_STOCK_CODES[index] || `688${900 + seed}.SH`,
      stockName: SAMPLE_STOCK_DISPLAY_NAMES[index] || `样本股票${seed}`,
      winRate,
      roi,
      holdDays,
    };
  });
}

export function buildCapitalSampleStockRows(metrics) {
  const count = Math.max(10, Math.min(15, metrics.stockCount || 10));
  const avgPnl = Number(metrics.avgPnlPerTrade || 0);
  const avgTradesPerStock = Number(metrics.avgTradesPerStock || 1);
  return Array.from({ length: count }).map((_, index) => {
    const seed = index + 1;
    const tradeCount = Math.max(1, Math.round(avgTradesPerStock + (seed % 6) * 0.8));
    const pnl = Math.round(avgPnl * tradeCount * (0.7 + (seed % 7) * 0.18) - ((seed % 4) * 1200));
    const winRate = Math.max(20, Math.min(92, Number((metrics.winRatePct + (seed % 5) * 3 - 6).toFixed(1))));
    return {
      id: `${SAMPLE_STOCK_CODES[index] || `688${910 + seed}.SH`}-${seed}`,
      stockCode: SAMPLE_STOCK_CODES[index] || `688${910 + seed}.SH`,
      stockName: SAMPLE_STOCK_DISPLAY_NAMES[index] || `样本股票${seed}`,
      tradeCount,
      pnl,
      winRate,
    };
  });
}
