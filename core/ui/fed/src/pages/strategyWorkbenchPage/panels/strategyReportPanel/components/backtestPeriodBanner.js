import React from 'react';
import { Typography } from '@mui/material';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import {
  BACKTEST_PERIOD_TOOLTIP,
  formatBacktestPeriodLine,
  readBacktestPeriodFromSlot,
} from '../lib/backtestPeriodDisplay';

export default function BacktestPeriodBanner({ slot }) {
  const period = readBacktestPeriodFromSlot(slot);
  const line = formatBacktestPeriodLine(period);
  if (!line) return null;

  return (
    <Typography
      variant="body2"
      color="text.secondary"
      className="ntq-backtest-period-banner"
      component="div"
    >
      {line}
      <NtqHelpTooltip title={BACKTEST_PERIOD_TOOLTIP} />
    </Typography>
  );
}
