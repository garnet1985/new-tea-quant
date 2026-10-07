import React from 'react';
import { Typography } from '@mui/material';
import TipLabel from 'views/tipLabel';
import './style.scss';

function MetricCard({ title, value, hint, titleTip }) {
  return (
    <div className="ntq-metric-card">
      <div className="ntq-metric-card__body">
        <TipLabel variant="caption" tip={titleTip}>
          {title}
        </TipLabel>
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
