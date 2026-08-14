import React from 'react';
import PropTypes from 'prop-types';
import { Typography } from '@mui/material';
import {
  REPORT_BLOCK_UNAVAILABLE_ZH,
  REPORT_EMPTY_MATCH_ZH,
} from '../../../reportMetrics/strategyReportMetricsNormalize';

/** 报告区块缺数据 / 空结果时的统一提示 */
function ReportUnavailableHint({ message = REPORT_BLOCK_UNAVAILABLE_ZH }) {
  return (
    <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
      {message}
    </Typography>
  );
}

ReportUnavailableHint.propTypes = {
  message: PropTypes.string,
};

ReportUnavailableHint.defaultProps = {
  message: REPORT_BLOCK_UNAVAILABLE_ZH,
};

export { REPORT_EMPTY_MATCH_ZH };
export default ReportUnavailableHint;
