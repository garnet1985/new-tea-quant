import React, { useRef } from 'react';
import { InputAdornment, TextField as MuiTextField } from '@mui/material';
import Icon from 'ui/icon/icon';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import { inputChromeClass } from 'ui/input/controlChrome';
import '../_control.scss';

/**
 * 日期。value 为 `YYYY-MM-DD` 字符串；onChange 为 e.target.value。
 * 日历图标用自绘浅色 icon（隐藏 UA 黑色原生指示器）。
 *
 * @example
 * <Date label="开始日" value={d} onChange={(e) => setD(e.target.value)} />
 */
function Date({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  required = false,
  value,
  onChange,
  disabled = false,
  name = '',
  id = '',
  className = '',
  fullWidth = true,
  /** 默认限制约 320px；传 false 去掉上限 */
  maxWidth = true,
  surface = 'solid',
  radius = 'sm',
  ...rest
}) {
  const controlId = useControlId(id);
  const inputRef = useRef(null);
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const widthClass = maxWidth ? 'ntq-input--capped' : 'ntq-input--fluid';
  const chromeClass = inputChromeClass({ surface, radius });

  const {
    InputProps: restInputProps,
    inputProps: restInputPropsInner,
    ...fieldRest
  } = rest;

  const openPicker = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (disabled) return;
    const el = inputRef.current;
    if (!el) return;
    if (typeof el.showPicker === 'function') {
      try {
        el.showPicker();
        return;
      } catch (_) {
        // 部分环境会抛 NotAllowedError，退回 focus
      }
    }
    el.focus();
    el.click();
  };

  const control = (
    <MuiTextField
      id={controlId}
      name={name || undefined}
      size="small"
      type="date"
      value={value ?? ''}
      onChange={onChange}
      disabled={disabled}
      fullWidth={fullWidth}
      error={Boolean(error)}
      className={[
        'ntq-date',
        widthClass,
        chromeClass,
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      InputLabelProps={{ shrink: true }}
      inputRef={inputRef}
      InputProps={{
        ...restInputProps,
        endAdornment: (
          <InputAdornment position="end" className="ntq-date__adornment">
            <button
              type="button"
              className="ntq-date__picker-btn"
              aria-label="选择日期"
              tabIndex={-1}
              disabled={disabled}
              onClick={openPicker}
              onMouseDown={(e) => e.preventDefault()}
            >
              <Icon name="calendar" size="sm" tone="muted" />
            </button>
            {restInputProps?.endAdornment}
          </InputAdornment>
        ),
      }}
      inputProps={{
        ...restInputPropsInner,
        className: ['ntq-date__input', restInputPropsInner?.className].filter(Boolean).join(' '),
        'aria-label': placement === 'none'
          ? (label || fieldRest['aria-label'] || '日期')
          : restInputPropsInner?.['aria-label'],
      }}
      {...fieldRest}
    />
  );

  if (!hasFieldChrome) {
    return control;
  }

  return (
    <Field
      label={label}
      labelPlacement={placement}
      tip={tip}
      hint={hint}
      error={error}
      htmlFor={controlId}
      required={required}
      bindControlId={false}
      className={[widthClass, className].filter(Boolean).join(' ')}
    >
      {control}
    </Field>
  );
}

export default Date;
