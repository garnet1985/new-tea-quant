import React from 'react';
import { HelpTooltip } from 'ui';
import './style.scss';
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
    <div className="ntq-backtest-period-banner ntq-muted">
      {line}
      <HelpTooltip title={BACKTEST_PERIOD_TOOLTIP} />
    </div>
  );
}
