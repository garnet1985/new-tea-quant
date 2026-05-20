import React from 'react';
import PropTypes from 'prop-types';
import EditorFieldLabel from './editorFieldLabel';
import './editorFieldGroup.scss';

/**
 * 编辑器内轻量分组：标题在框外，字段在带边框的内容区里。
 * 比通用 Paper 更留白，用于「到期设置」等逻辑相关的字段簇。
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

  return (
    <div className={rootClass}>
      {label && !plain ? (
        <EditorFieldLabel
          field={{ label, tooltip: tooltip || '' }}
          context={context}
          sx={{ mb: 1 }}
        />
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
  /** 无标题容器：仅保留子项纵向间距，不画框 */
  plain: PropTypes.bool,
  className: PropTypes.string,
};
