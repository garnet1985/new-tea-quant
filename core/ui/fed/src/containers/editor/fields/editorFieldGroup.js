import React from 'react';
import PropTypes from 'prop-types';
import TipLabel from 'views/tipLabel';
import './style.scss';

/**
 * 编辑器内轻量分组：区块标题在上，字段在下。
 * 默认字段区带边框；`plain` 时不画框、不额外 padding（仅纵向间距）。
 */
export default function EditorFieldGroup({
  label,
  tooltip,
  context = {},
  children,
  plain = false,
  className = '',
}) {
  const rootClass = [
    'ntq-editor-field-group',
    plain ? 'ntq-editor-field-group--plain' : '',
    className,
  ].filter(Boolean).join(' ');

  const bodyClass = [
    'ntq-editor-field-group__body',
    plain ? 'ntq-editor-field-group__body--plain' : '',
  ].filter(Boolean).join(' ');

  const shine = Boolean(context?.defaultTooltipShine);

  return (
    <div className={rootClass}>
      {label ? (
        <TipLabel
          tip={tooltip}
          shine={shine}
          component="h3"
          className="ntq-editor-field-group__title"
          textClassName="ntq-editor-field-group__title-text"
        >
          {label}
        </TipLabel>
      ) : null}
      <div className={bodyClass}>{children}</div>
    </div>
  );
}

EditorFieldGroup.propTypes = {
  label: PropTypes.string,
  tooltip: PropTypes.string,
  context: PropTypes.object,
  children: PropTypes.node,
  /** 无边框：仅保留子项纵向间距，不画框、不额外 padding */
  plain: PropTypes.bool,
  className: PropTypes.string,
};
