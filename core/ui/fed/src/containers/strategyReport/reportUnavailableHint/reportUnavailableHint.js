import React from 'react';
import PropTypes from 'prop-types';
import {
  REPORT_BLOCK_UNAVAILABLE_ZH,
  REPORT_EMPTY_MATCH_ZH,
} from '../reportMetrics/strategyReportMetricsNormalize';
import './style.scss';

/** 报告区块缺数据 / 空结果时的统一提示 */
function ReportUnavailableHint({ message = REPORT_BLOCK_UNAVAILABLE_ZH }) {
  return (
    <p className="ntq-report-unavailable-hint ntq-muted">
      {message}
    </p>
  );
}

ReportUnavailableHint.propTypes = {
  message: PropTypes.string,
};

export { REPORT_EMPTY_MATCH_ZH };
export default ReportUnavailableHint;
