import React from 'react';
import DateRangeInput from 'components/dateRangeInput/DateRangeInput';
import { getByPath, setByPath } from '../editor.helper';

function DateRangeField({ field, value, errors, onChange, emitChangeMeta }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }

  const startPath = field.startName;
  const endPath = field.endName;
  const startValue = getByPath(value, startPath) || '';
  const endValue = getByPath(value, endPath) || '';
  const startError = errors?.[startPath] || '';
  const endError = errors?.[endPath] || '';

  const apply = (nextStart, nextEnd, changedKey) => {
    if (!onChange) return;
    let updated = setByPath(value, startPath, nextStart || '');
    updated = setByPath(updated, endPath, nextEnd || '');

    const syncTargets = Array.isArray(field.syncTargets) ? field.syncTargets : [];
    syncTargets.forEach((target) => {
      if (!target?.startName || !target?.endName) return;
      updated = setByPath(updated, target.startName, nextStart || '');
      updated = setByPath(updated, target.endName, nextEnd || '');
    });

    onChange(updated);
    if (emitChangeMeta) {
      emitChangeMeta(updated, {
        name: field.name,
        value: { start: nextStart || '', end: nextEnd || '' },
        changedKey,
      });
    }
  };

  return (
    <DateRangeInput
      label={field.label}
      tooltipTitle={field.tooltip}
      startLabel={field.startLabel}
      endLabel={field.endLabel}
      startValue={startValue}
      endValue={endValue}
      onStartChange={(nextStart) => apply(nextStart, endValue, 'start')}
      onEndChange={(nextEnd) => apply(startValue, nextEnd, 'end')}
      startError={startError}
      endError={endError}
    />
  );
}

export default DateRangeField;
