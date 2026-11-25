import React from 'react';
import { TextField as MuiTextField } from '@mui/material';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import { inputChromeClass } from 'ui/input/controlChrome';
import '../_control.scss';

/**
 * 多行文本。标签布局走 Field。
 *
 * @example
 * <TextArea label="备注" rows={3} value={v} onChange={…} />
 */
function TextArea({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  required = false,
  value,
  onChange,
  placeholder = '',
  disabled = false,
  rows = 3,
  name = '',
  id = '',
  className = '',
  fullWidth = true,
  /** 默认限制约 400px；传 false 去掉上限 */
  maxWidth = true,
  surface = 'solid',
  radius = 'sm',
  ...rest
}) {
  const controlId = useControlId(id);
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const minRows = Number(rows) > 0 ? Number(rows) : 3;
  const widthClass = maxWidth ? 'ntq-input--capped-area' : 'ntq-input--fluid';
  const chromeClass = inputChromeClass({ surface, radius });

  const {
    InputProps: restInputProps,
    inputProps: restInputPropsInner,
    sx: restSx,
    ...fieldRest
  } = rest;

  const control = (
    <MuiTextField
      id={controlId}
      name={name || undefined}
      size="small"
      multiline
      minRows={minRows}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      fullWidth={fullWidth}
      error={Boolean(error)}
      className={[
        'ntq-text-area',
        widthClass,
        chromeClass,
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      // 清掉 OutlinedInput wrapper padding，只留 textarea
      InputProps={{
        ...restInputProps,
        sx: [
          { padding: '0 !important' },
          restInputProps?.sx,
        ].filter(Boolean),
      }}
      inputProps={{
        ...restInputPropsInner,
        style: {
          padding: '0.5rem 0.75rem',
          ...(restInputPropsInner?.style || {}),
        },
        'aria-label': placement === 'none'
          ? (label || fieldRest['aria-label'] || placeholder || '多行输入')
          : restInputPropsInner?.['aria-label'],
      }}
      sx={restSx}
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

export default TextArea;
