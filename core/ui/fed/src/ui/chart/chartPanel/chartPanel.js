import React from 'react';
import ReactECharts from 'echarts-for-react';
import NtqHelpTooltip from 'ui/message/ntqHelpTooltip';
import Loading from 'ui/progress/loading';
import './style.scss';

/**
 * 图表壳：标题 / tip / note + ECharts。
 * 只收已拼好的 option；K 线 / 业务 series 由上层（L2）构建。
 *
 * @example
 * <ChartPanel title="分布" tip="说明" option={option} height={200} />
 * <ChartPanel title="加载中" loading height={180} />
 * <ChartPanel title="无数据" fallback={<p className="ntq-muted">暂无</p>} />
 */
function ChartPanel({
  title,
  tip,
  note,
  option,
  fallback = null,
  height = 180,
  framed = true,
  spaced = false,
  loading = false,
  onEvents,
  className = '',
  notMerge = true,
  lazyUpdate = true,
  ...rest
}) {
  const hasChart = Boolean(option) && !loading;
  const hasFallback = fallback != null && !loading && !option;
  if (!title && !hasChart && !hasFallback && !loading) {
    return null;
  }

  const rootClass = [
    'ntq-chart-panel',
    framed ? 'ntq-chart-panel--framed' : '',
    spaced ? 'ntq-chart-panel--spaced' : '',
    className,
  ].filter(Boolean).join(' ');

  const canvasStyle = {
    height: typeof height === 'number' ? `${height}px` : height,
    width: '100%',
  };

  return (
    <div className={rootClass} {...rest}>
      {title != null && title !== false ? (
        <div className="ntq-chart-panel__title-row">
          <span className="ntq-chart-panel__title ntq-caption">{title}</span>
          {tip ? <NtqHelpTooltip title={tip} /> : null}
        </div>
      ) : null}
      {note ? (
        <p className="ntq-chart-panel__note ntq-muted">{note}</p>
      ) : null}
      {loading ? (
        <div className="ntq-chart-panel__canvas ntq-chart-panel__canvas--loading" style={canvasStyle}>
          <Loading variant="inline" aria-label="图表加载中" />
        </div>
      ) : null}
      {hasChart ? (
        <div className="ntq-chart-panel__canvas">
          <ReactECharts
            option={option}
            style={canvasStyle}
            notMerge={notMerge}
            lazyUpdate={lazyUpdate}
            onEvents={onEvents}
          />
        </div>
      ) : null}
      {hasFallback ? (
        <div className="ntq-chart-panel__fallback" style={canvasStyle}>
          {fallback}
        </div>
      ) : null}
    </div>
  );
}

export default ChartPanel;
