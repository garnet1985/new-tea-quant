import React from 'react';
import { Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import TipLabel from 'views/tipLabel';
import './style.scss';

/** 带标题 / 说明的报告内嵌图。无 option 且无 fallback 时不渲染。 */
function ChartPanel({
  title,
  tip,
  option,
  height = 180,
  note,
  fallback,
  framed = true,
  spaced = false,
  onEvents,
}) {
  if (!option && fallback == null) return null;
  const rootClass = [
    'ntq-chart-panel',
    framed ? 'ntq-chart-panel--framed' : '',
    spaced ? 'ntq-chart-panel--spaced' : '',
  ].filter(Boolean).join(' ');
  return (
    <div className={rootClass}>
      <TipLabel variant="caption" tip={tip} className="ntq-tip-label--below">
        {title}
      </TipLabel>
      {note ? (
        <Typography variant="caption" color="text.secondary" className="ntq-chart-panel__note">
          {note}
        </Typography>
      ) : null}
      {option ? (
        <ReactECharts
          option={option}
          style={{ height, width: '100%' }}
          notMerge
          lazyUpdate
          onEvents={onEvents}
        />
      ) : fallback}
    </div>
  );
}

export default ChartPanel;
