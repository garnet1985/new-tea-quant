import React from 'react';
import Date from 'ui/input/date';
import Field from 'ui/input/field';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import '../_control.scss';

function emitRange(onChange, name, start, end) {
  if (typeof onChange !== 'function') return;
  onChange({
    target: {
      name: name || undefined,
      value: { start, end },
    },
  });
}

/**
 * 日期区间。value: `{ start, end }`（`YYYY-MM-DD`）；onChange 为 e.target.value。
 *
 * @example
 * <DateRange
 *   label="回测区间"
 *   value={{ start, end }}
 *   onChange={(e) => { setStart(e.target.value.start); setEnd(e.target.value.end); }}
 * />
 */
function DateRange({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  startError = '',
  endError = '',
  required = false,
  value,
  onChange,
  startLabel = '开始',
  endLabel = '结束',
  disabled = false,
  name = '',
  className = '',
  /** 每个日期默认 capped；false 时两格拉满 */
  maxWidth = true,
  ...rest
}) {
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const showSideLabels = !hasFieldChrome;
  const start = value?.start ?? '';
  const end = value?.end ?? '';
  const startErr = startError || '';
  const endErr = endError || '';

  const pair = (
    <div
      className={[
        'ntq-date-range',
        showSideLabels ? 'ntq-date-range--side-labels' : '',
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      {...rest}
    >
      {showSideLabels ? (
        <div className="ntq-date-range__labels" aria-hidden="true">
          <span className="ntq-date-range__side-label">{startLabel}</span>
          <span className="ntq-date-range__side-gap" />
          <span className="ntq-date-range__side-label">{endLabel}</span>
        </div>
      ) : null}
      <div className="ntq-date-range__controls">
        <Date
          labelPlacement="none"
          value={start}
          onChange={(e) => emitRange(onChange, name, e.target.value, end)}
          error={startErr}
          disabled={disabled}
          maxWidth={maxWidth}
          fullWidth={false}
          aria-label={startLabel}
        />
        <span className="ntq-date-range__sep ntq-muted" aria-hidden="true">–</span>
        <Date
          labelPlacement="none"
          value={end}
          onChange={(e) => emitRange(onChange, name, start, e.target.value)}
          error={endErr}
          disabled={disabled}
          maxWidth={maxWidth}
          fullWidth={false}
          aria-label={endLabel}
        />
      </div>
    </div>
  );

  if (!hasFieldChrome) {
    return pair;
  }

  return (
    <Field
      label={label}
      labelPlacement={placement}
      tip={tip}
      hint={hint}
      error={error}
      required={required}
      htmlFor={false}
      bindControlId={false}
      className={className}
    >
      {pair}
    </Field>
  );
}

export default DateRange;
