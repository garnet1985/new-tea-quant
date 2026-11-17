import React from 'react';
import { Loading } from 'ui';
import ReportStockSampleGrid from '../reportStockSampleGrid';
import ReportUnavailableHint, {
  REPORT_EMPTY_MATCH_ZH,
} from '../reportUnavailableHint';

/** 逐股表：加载 / 遮罩 / 空态包一层，列与排序仍由调用方传入。 */
function ReportStockGridSection({
  loading = false,
  overlay = null,
  filteredRows,
  loadingMessage = '正在加载逐股数据…',
  hideWhenEmpty = true,
  emptyFallback,
  ...gridProps
}) {
  if (loading) {
    return (
      <div className="ntq-report-stock-grid-section">
        <Loading variant="inline" message={loadingMessage} className="is-block" />
      </div>
    );
  }

  const hasRows = Array.isArray(filteredRows) && filteredRows.length > 0;
  const showTable = Boolean(overlay || hasRows || !hideWhenEmpty);
  if (!showTable) {
    return emptyFallback === undefined
      ? <ReportUnavailableHint message={REPORT_EMPTY_MATCH_ZH} />
      : emptyFallback;
  }

  return (
    <div className="ntq-report-stock-grid-section">
      {overlay}
      <ReportStockSampleGrid rows={filteredRows} {...gridProps} />
    </div>
  );
}

export default ReportStockGridSection;
