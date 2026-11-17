import React from 'react';
import { Date, DateRange } from 'ui';
import EditorFieldLabel from './fields/editorFieldLabel';
import './fields/style.scss';

/**
 * 通用时间段输入：标签 + 可选说明 + 起止日期。
 * 水平布局走 ui DateRange；垂直布局叠两个 Date。
 */
export default function DateRangeInput({
  label,
  tooltipTitle,
  context = {},
  layout = 'horizontal',
  startLabel = '开始',
  endLabel = '结束',
  startValue = '',
  endValue = '',
  onStartChange,
  onEndChange,
  startError = '',
  endError = '',
}) {
  const isVertical = layout === 'vertical';

  return (
    <div
      className={[
        'ntq-editor-date-range',
        isVertical ? 'ntq-editor-date-range--vertical' : '',
      ].filter(Boolean).join(' ')}
    >
      {label ? (
        <EditorFieldLabel
          field={{ label, tooltip: tooltipTitle || '' }}
          context={context}
          noMargin
        />
      ) : null}

      {isVertical ? (
        <div className="ntq-editor-date-range__stack">
          <Date
            label={startLabel}
            maxWidth={false}
            value={startValue || ''}
            onChange={(e) => onStartChange?.(e.target.value)}
            error={startError || undefined}
          />
          <Date
            label={endLabel}
            maxWidth={false}
            value={endValue || ''}
            onChange={(e) => onEndChange?.(e.target.value)}
            error={endError || undefined}
          />
        </div>
      ) : (
        <DateRange
          labelPlacement="none"
          maxWidth={false}
          startLabel={startLabel}
          endLabel={endLabel}
          value={{ start: startValue || '', end: endValue || '' }}
          startError={startError}
          endError={endError}
          onChange={(e) => {
            const next = e?.target?.value || {};
            if (next.start !== startValue) onStartChange?.(next.start || '');
            if (next.end !== endValue) onEndChange?.(next.end || '');
          }}
        />
      )}
    </div>
  );
}
