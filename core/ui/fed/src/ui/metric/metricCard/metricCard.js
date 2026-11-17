import React from 'react';
import HelpTooltip from 'ui/message/helpTooltip';
import './style.scss';

/**
 * 报告指标卡：标题 + 主值 + 可选 hint。
 * tip / titleTip：标题旁说明（优先 tip；titleTip 兼容旧调用）。
 *
 * @example
 * <MetricCard title="机会总数" value="128" tip="统计窗口内触发次数" />
 * <MetricCard title="涨停无法买入" value="12 / 100" hint="占比 12%" />
 */
function MetricCard({
  title,
  value,
  hint,
  tip,
  titleTip,
  className = '',
  ...rest
}) {
  const help = tip != null && tip !== false ? tip : titleTip;
  const rootClass = ['ntq-metric-card', className].filter(Boolean).join(' ');

  return (
    <div className={rootClass} {...rest}>
      <div className="ntq-metric-card__title-row">
        <span className="ntq-metric-card__title ntq-caption">{title}</span>
        {help ? <HelpTooltip title={help} /> : null}
      </div>
      <div className="ntq-metric-card__value">{value}</div>
      {hint ? (
        <div className="ntq-metric-card__hint ntq-muted">{hint}</div>
      ) : null}
    </div>
  );
}

export default MetricCard;
