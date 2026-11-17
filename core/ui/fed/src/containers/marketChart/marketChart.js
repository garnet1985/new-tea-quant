import React from 'react';
import ReactECharts from 'echarts-for-react';
import TipLabel from 'ui/title/tipLabel';
import { buildMarketChartOption } from './buildMarketChartOption';
import './marketChart.scss';

/**
 * 无业务语义市场图壳：传入 MarketChartModel 或已构建的 option。
 */
function MarketChart({
  model,
  option: optionProp,
  title,
  tip,
  note,
  height = 420,
  fallback,
  framed = false,
  className = '',
  style,
}) {
  const option = optionProp || (model ? buildMarketChartOption(model) : null);
  if ((!option || !Object.keys(option).length) && fallback == null) return null;

  const rootClass = [
    'ntq-market-chart',
    framed ? 'ntq-market-chart--framed' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style}>
      <TipLabel variant="caption" tip={tip} className="ntq-tip-label--below">
        {title}
      </TipLabel>
      {note ? (
        <p className="ntq-market-chart__note">{note}</p>
      ) : null}
      {option && Object.keys(option).length > 0 ? (
        <ReactECharts
          option={option}
          style={{ height, width: '100%' }}
          notMerge
          lazyUpdate
        />
      ) : fallback}
    </div>
  );
}

export default MarketChart;
