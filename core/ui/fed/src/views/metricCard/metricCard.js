import React from 'react';
import { Typography } from '@mui/material';
import NtqHelpTooltip from 'views/ntqHelpTooltip';
import './style.scss';

function MetricCard({ title, value, hint, titleTip }) {
  return (
    <div className="ntq-metric-card">
      <div className="ntq-metric-card__body">
        <div className="ntq-metric-card__title">
          <Typography variant="caption" color="text.secondary">{title}</Typography>
          {titleTip ? <NtqHelpTooltip title={titleTip} /> : null}
        </div>
        <Typography variant="h6" className="ntq-metric-card__value">
          {value}
        </Typography>
        {hint ? (
          <Typography variant="caption" color="text.secondary" className="ntq-metric-card__hint">
            {hint}
          </Typography>
        ) : null}
      </div>
    </div>
  );
}

export default MetricCard;
