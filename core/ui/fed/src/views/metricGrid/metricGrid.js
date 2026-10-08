import React from 'react';
import './style.scss';

function columnClass(columns) {
  if (columns === 4) return 'ntq-metric-grid--cols-4';
  if (columns === 3) return 'ntq-metric-grid--cols-3';
  return 'ntq-metric-grid--cols-2';
}

/** MetricCard 网格：报告区块共用。 */
function MetricGrid({ columns = 2, denseXs = false, children }) {
  const rootClass = [
    'ntq-metric-grid',
    columnClass(columns),
    denseXs ? 'ntq-metric-grid--dense' : '',
  ].filter(Boolean).join(' ');
  return (
    <div className={rootClass}>
      {children}
    </div>
  );
}

export default MetricGrid;
