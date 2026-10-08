import { useMemo, useState } from 'react';

/** 逐股表：按代码 / 名称本地过滤。 */
export function useReportStockSearch(stockRows) {
  const [stockSearch, setStockSearch] = useState('');
  const derivedStockRows = useMemo(
    () => (Array.isArray(stockRows) && stockRows.length > 0 ? stockRows : []),
    [stockRows],
  );
  const filteredRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    if (!keyword) return derivedStockRows;
    return derivedStockRows.filter((row) => {
      const code = String(row?.stockCode || '').toLowerCase();
      const name = String(row?.stockName || '').toLowerCase();
      return code.includes(keyword) || name.includes(keyword);
    });
  }, [derivedStockRows, stockSearch]);
  return { stockSearch, setStockSearch, derivedStockRows, filteredRows };
}
