import React from 'react';
import { Box } from '@mui/material';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';
import ReportUnavailableHint, {
  REPORT_EMPTY_MATCH_ZH,
} from './reportUnavailableHint';

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
      <Box sx={{ position: 'relative' }}>
        <InlineLoadingState block compact message={loadingMessage} />
      </Box>
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
    <Box sx={{ position: 'relative' }}>
      {overlay}
      <ReportStockSampleGrid rows={filteredRows} {...gridProps} />
    </Box>
  );
}

export default ReportStockGridSection;
