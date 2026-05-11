/** 与 ``sortMappedEnumRows`` 字段一致；仅用于首屏默认顺序（后续排序为 DataGrid 客户端） */
export const ENUM_REF_DEFAULT_SORT = { sortBy: 'opportunities', order: 'desc' };

export function mapStockRefToRows(stockRef) {
  if (!stockRef || typeof stockRef !== 'object') return [];
  return Object.entries(stockRef).map(([code, v]) => {
    const row = v && typeof v === 'object' ? v : {};
    const opp = row.opportunities ?? row.opportunity_count ?? row.opportunityCount;
    return {
      id: String(code),
      stockCode: String(code),
      stockName: String(row.stock_name || row.stockName || code),
      opportunities: Number(opp ?? 0),
      completionRate: Number(row.completion_rate ?? row.completionRate ?? 0),
      triggerSpanDays: Number(row.avg_opportunity_interval_days ?? row.triggerSpanDays ?? 0),
    };
  });
}

/** JSON object 键顺序不可靠：映射成行数组后按维度排序一次，便于首屏与分页。 */
export function sortMappedEnumRows(rows, sortBy, order) {
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
      case 'completion_rate':
        cmp = Number(a.completionRate) - Number(b.completionRate);
        break;
      case 'avg_opportunity_interval_days':
        cmp = Number(a.triggerSpanDays) - Number(b.triggerSpanDays);
        break;
      case 'opportunities':
      default:
        cmp = Number(a.opportunities) - Number(b.opportunities);
        break;
    }
    if (cmp !== 0) return desc ? -cmp : cmp;
    return tie(a, b);
  });
}
