import React from 'react';
import { Typography } from '@mui/material';
import { REPORT_BLOCK_UNAVAILABLE_ZH } from '../../../reportMetrics/strategyReportMetricsNormalize';

/** 报告区块缺数据时的统一提示（与枚举/价格子面板原 ``UnavailableHint`` 一致） */
function ReportUnavailableHint() {
  return (
    <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
      {REPORT_BLOCK_UNAVAILABLE_ZH}
    </Typography>
  );
}

export default ReportUnavailableHint;
