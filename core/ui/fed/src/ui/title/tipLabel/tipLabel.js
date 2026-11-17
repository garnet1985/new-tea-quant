import React from 'react';
import HelpTooltip from 'ui/message/helpTooltip';
import './style.scss';

const VARIANT_CLASS = {
  section: 'ntq-tip-label__text--section',
  caption: 'ntq-tip-label__text--caption',
  field: 'ntq-tip-label__text--field',
  title: 'ntq-tip-label__text--title',
};

/**
 * 一行文字 + 可选说明。variant 只改字号层级。
 *
 * @example
 * <TipLabel tip="字段说明">市场规则</TipLabel>
 * <TipLabel variant="title" tip="…" shine>全局设置</TipLabel>
 */
function TipLabel({
  children,
  tip = '',
  shine = false,
  variant = 'section',
  className = '',
  textClassName = '',
  component,
  placement,
}) {
  const hasText = children != null && children !== '';
  if (!hasText && !tip) return null;

  const rootClass = ['ntq-tip-label', className].filter(Boolean).join(' ');
  const Tag = component || 'span';
  const textClass = [
    'ntq-tip-label__text',
    textClassName || VARIANT_CLASS[variant] || VARIANT_CLASS.section,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass}>
      {hasText ? (
        <Tag className={textClass}>{children}</Tag>
      ) : null}
      {tip ? (
        <HelpTooltip
          title={tip}
          shine={shine}
          placement={placement || 'top'}
        />
      ) : null}
    </div>
  );
}

export default TipLabel;
