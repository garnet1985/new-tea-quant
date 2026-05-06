/**
 * 执行面板：本地模拟运行结果（后续由真实任务轮询/WebSocket 替换）
 */

export function simulateEnumResult(settings) {
  const base = Number(settings?.sampling?.sampling_amount || 10);
  return {
    opportunities: Math.max(1, Math.round(base * (4 + Math.random() * 5))),
  };
}

export function simulatePriceResult() {
  const winRate = Number((40 + Math.random() * 40).toFixed(1));
  const roi = Number((Math.random() * 50 - 10).toFixed(1));
  const avgHoldDays = Number((5 + Math.random() * 25).toFixed(1));
  return { winRate, roi, avgHoldDays };
}

export function simulateCapitalResult(settings) {
  const initialCapital = Number(settings?.capital_simulator?.initial_capital || 1000000);
  const retPct = Number((Math.random() * 40 - 8).toFixed(1));
  const endCapital = Math.round(initialCapital * (1 + retPct / 100));
  const profit = endCapital - initialCapital;
  return { initialCapital, endCapital, profit, retPct };
}
