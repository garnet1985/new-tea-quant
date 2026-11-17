import React from 'react';
import { TipLabel } from 'ui';

/** 标签与下方控件的间距 */
export const EDITOR_FIELD_LABEL_MB = '0.5rem';

/** 表单字段标签：field 字号 + 可选 HelpTooltip */
export default function EditorFieldLabel({
  field,
  context = {},
  tooltipTitle,
  className = '',
  noMargin = false,
}) {
  if (!field?.label) return null;
  const title = tooltipTitle ?? field.tooltip ?? '';
  const shine = field.tooltipShine ?? context?.defaultTooltipShine ?? false;

  return (
    <div
      className={[
        'ntq-editor-field-label',
        noMargin ? 'ntq-editor-field-label--flush' : '',
        className,
      ].filter(Boolean).join(' ')}
    >
      <TipLabel variant="field" tip={title} shine={shine}>
        {field.label}
      </TipLabel>
    </div>
  );
}
