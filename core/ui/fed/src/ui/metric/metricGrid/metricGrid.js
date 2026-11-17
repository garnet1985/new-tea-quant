import React from 'react';
import { METRIC_GRID_COLUMN_TOKENS } from 'ui/tokens';
import './style.scss';

function columnClass(columns) {
  if (columns === 4) return 'ntq-metric-grid--cols-4';
  if (columns === 3) return 'ntq-metric-grid--cols-3';
  return 'ntq-metric-grid--cols-2';
}

/**
 * MetricCard 网格。窄屏 1 列；denseXs 时窄屏 2 列；≥900px 按 columns。
 *
 * @example
 * <MetricGrid columns={2}>
 *   <MetricCard title="A" value="1" />
 *   <MetricCard title="B" value="2" />
 * </MetricGrid>
 */
function MetricGrid({
  columns = 2,
  denseXs = false,
  className = '',
  children,
  ...rest
}) {
  const cols = METRIC_GRID_COLUMN_TOKENS.includes(columns) ? columns : 2;
  const rootClass = [
    'ntq-metric-grid',
    columnClass(cols),
    denseXs ? 'ntq-metric-grid--dense' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} {...rest}>
      {children}
    </div>
  );
}

export default MetricGrid;
