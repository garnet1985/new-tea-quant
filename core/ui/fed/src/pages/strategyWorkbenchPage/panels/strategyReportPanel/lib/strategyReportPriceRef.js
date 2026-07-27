/** 与 ``sortMappedPriceRows`` 字段一致；仅用于首屏默认顺序 */
export const PRICE_REF_DEFAULT_SORT = { sortBy: 'avg_roi', order: 'desc' };

/** 价格回测逐股 ref（``entity_list.json`` / legacy ``0_stock_ref.json``，snake_case）。 */
export function mapPriceStockRefToRows(stockRef) {
  if (!stockRef || typeof stockRef !== 'object') return [];
  return Object.entries(stockRef).map(([code, v]) => {
    const row = v && typeof v === 'object' ? v : {};
    const avgRoiRaw = Number(row.avg_roi ?? 0);
    const avgRoi = Number.isFinite(avgRoiRaw) && Math.abs(avgRoiRaw) < 1
      ? avgRoiRaw * 100
      : avgRoiRaw;
    return {
      id: String(code),
      stockCode: String(code),
      stockName: String(row.stock_name || code),
      winRate: Number(row.win_rate ?? 0),
      avgRoi: Number.isFinite(avgRoi) ? avgRoi : 0,
      avgDurationDays: Number(row.avg_duration_in_days ?? 0),
      expirationRatio: Number(row.expiration_ratio ?? 0),
      totalInvestments: Number(row.total_investments ?? 0),
    };
  });
}

export function sortMappedPriceRows(rows, sortBy, order) {
  if (!Array.isArray(rows) || rows.length <= 1) return rows;
  const desc = order === 'desc';
  const tie = (a, b) => String(a.stockCode).localeCompare(String(b.stockCode), undefined, { numeric: true });
  return [...rows].sort((a, b) => {
    let cmp = 0;
    switch (sortBy) {
      case 'stock_code':
        cmp = String(a.stockCode).localeCompare(String(b.stockCode), undefined, { numeric: true });
        break;
      case 'stock_name':
        cmp = String(a.stockName).localeCompare(String(b.stockName), undefined, { numeric: true });
        break;
      case 'avg_roi':
        cmp = Number(a.avgRoi) - Number(b.avgRoi);
        break;
      case 'avg_duration_in_days':
        cmp = Number(a.avgDurationDays) - Number(b.avgDurationDays);
        break;
      case 'expiration_ratio':
        cmp = Number(a.expirationRatio) - Number(b.expirationRatio);
        break;
      case 'win_rate':
      default:
        cmp = Number(a.winRate) - Number(b.winRate);
        break;
    }
    if (cmp !== 0) return desc ? -cmp : cmp;
    return tie(a, b);
  });
}
