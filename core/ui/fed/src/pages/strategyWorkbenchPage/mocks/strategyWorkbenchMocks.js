/**
 * 策略工作台预留草图常量（对比下拉、样本股票代码等）。
 * 资金报告已不再使用 ``MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION`` 作为 UI 回落；保留供 Story / 后续接线参考。
 */

/** 报告对比 / 执行面板对比下拉共用版本键 */
export const STRATEGY_WORKBENCH_COMPARE_VERSION_OPTIONS = ['latest', 'v3', 'v2', 'v1'];

/** 报告「对比版本」枚举机会数 mock（按版本） */
export const MOCK_REPORT_ENUM_OPPORTUNITIES_BY_VERSION = {
  latest: 100,
  v3: 108,
  v2: 103,
  v1: 115,
};

/** 报告「对比版本」价格回测摘要 mock（按版本） */
export const MOCK_REPORT_PRICE_SUMMARIES_BY_VERSION = {
  latest: { winRate: 56.2, roi: 18.4, avgHoldDays: 13.1 },
  v3: { winRate: 52.8, roi: 12.6, avgHoldDays: 16.2 },
  v2: { winRate: 49.6, roi: 9.3, avgHoldDays: 14.5 },
  v1: { winRate: 44.1, roi: 6.7, avgHoldDays: 18.9 },
};

/** 报告「对比版本」资金模拟摘要 mock（按版本） */
export const MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION = {
  latest: { totalReturnPct: 31.8, maxDrawdownPct: 9.6, winRatePct: 57.1 },
  v3: { totalReturnPct: 24.6, maxDrawdownPct: 11.4, winRatePct: 54.2 },
  v2: { totalReturnPct: 19.2, maxDrawdownPct: 12.9, winRatePct: 51.0 },
  v1: { totalReturnPct: 13.7, maxDrawdownPct: 15.6, winRatePct: 47.8 },
};

/**
 * 执行面板「对比版本」下拉：各步骤一行展示用的 mock（与报告维度对齐）
 */
export const MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION = {
  latest: {
    enum: { opportunities: 100 },
    price: { winRate: 56.2, roi: 18.4 },
    capital: { initialCapital: 1000000, endCapital: 1031800, profit: 31800, retPct: 31.8 },
  },
  v3: {
    enum: { opportunities: 108 },
    price: { winRate: 52.8, roi: 12.6 },
    capital: { initialCapital: 1000000, endCapital: 1065000, profit: 65000, retPct: 6.5 },
  },
  v2: {
    enum: { opportunities: 103 },
    price: { winRate: 49.6, roi: 9.3 },
    capital: { initialCapital: 1000000, endCapital: 1042000, profit: 42000, retPct: 4.2 },
  },
  v1: {
    enum: { opportunities: 115 },
    price: { winRate: 44.1, roi: 6.7 },
    capital: { initialCapital: 1000000, endCapital: 1020000, profit: 20000, retPct: 2.0 },
  },
};

/** 样本股票名称池（报告 DataGrid 生成用） */
export const SAMPLE_STOCK_DISPLAY_NAMES = [
  '贵州茅台',
  '五粮液',
  '中国平安',
  '招商银行',
  '美的集团',
  '比亚迪',
  '隆基绿能',
  '宁德时代',
  '中芯国际',
  '海康威视',
  '恒瑞医药',
  '中国中免',
  '紫金矿业',
  '迈瑞医疗',
  '中信证券',
  '药明康德',
  '万华化学',
  '立讯精密',
];

/** 样本股票代码池（报告 DataGrid 生成用） */
export const SAMPLE_STOCK_CODES = [
  '600519.SH',
  '000858.SZ',
  '601318.SH',
  '600036.SH',
  '000333.SZ',
  '002594.SZ',
  '601012.SH',
  '300750.SZ',
  '688981.SH',
  '002415.SZ',
  '600276.SH',
  '601888.SH',
  '601899.SH',
  '300760.SZ',
  '600030.SH',
  '603259.SH',
  '600309.SH',
  '002475.SZ',
];
