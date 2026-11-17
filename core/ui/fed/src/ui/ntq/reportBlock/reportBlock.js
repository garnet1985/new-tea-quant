import React from 'react';
import NtqHelpTooltip from 'ui/message/ntqHelpTooltip';
import './style.scss';

/**
 * 报告区块固定模板（回测 / 枚举报告等）。
 * 统一：描边浅底 + 标题行（可选 tip / 右侧 action）+ 内容区。
 * 内部指标用 MetricCard / MetricGrid；图用 ChartPanel——不要另起一套壳。
 *
 * @example
 * <ReportBlock title="机会盘点" tip="统计窗口内触发次数">
 *   <MetricGrid>…</MetricGrid>
 * </ReportBlock>
 */
function ReportBlock({
  title,
  tip,
  action = null,
  children,
  className = '',
  ...rest
}) {
  const rootClass = ['ntq-report-block', className].filter(Boolean).join(' ');
  const showHead = (title != null && title !== false) || Boolean(tip) || Boolean(action);

  return (
    <section className={rootClass} {...rest}>
      <div className="ntq-report-block__body">
        {showHead ? (
          <div className="ntq-report-block__head">
            <div className="ntq-report-block__title-row">
              {title != null && title !== false ? (
                <h3 className="ntq-report-block__title">{title}</h3>
              ) : null}
              {tip ? <NtqHelpTooltip title={tip} /> : null}
            </div>
            {action ? (
              <div className="ntq-report-block__action">{action}</div>
            ) : null}
          </div>
        ) : null}
        <div className="ntq-report-block__content">{children}</div>
      </div>
    </section>
  );
}

export default ReportBlock;
