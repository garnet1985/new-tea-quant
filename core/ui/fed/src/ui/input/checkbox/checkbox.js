import React from 'react';
import { Checkbox as MuiCheckbox } from '@mui/material';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import '../_control.scss';

/**
 * 复选框。`label` 为控件右侧文案；字段级标签仍可用 Field（labelPlacement）。
 *
 * @example
 * <Checkbox label="启用" checked={on} onChange={…} />
 * <Checkbox fieldLabel="选项" label="同意条款" tip="必读" />
 */
function Checkbox({
  label = '',
  fieldLabel = '',
  labelPlacement = 'none',
  tip = '',
  hint = '',
  error = '',
  required = false,
  checked = false,
  onChange,
  disabled = false,
  name = '',
  id = '',
  className = '',
  ...rest
}) {
  const controlId = useControlId(id);
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'none');
  const hasFieldChrome = Boolean(fieldLabel) || placement !== 'none' || tip || hint || error;
  const { inputProps: restInputProps, ...checkRest } = rest;

  const control = (
    <span className={['ntq-checkbox', disabled ? 'is-disabled' : '', !hasFieldChrome ? className : ''].filter(Boolean).join(' ')}>
      <MuiCheckbox
        name={name || undefined}
        size="small"
        checked={Boolean(checked)}
        onChange={onChange}
        disabled={disabled}
        inputProps={{
          id: controlId,
          'aria-label': label || fieldLabel || checkRest['aria-label'] || '复选',
          ...(restInputProps || {}),
        }}
        {...checkRest}
      />
      {label ? (
        <label className="ntq-checkbox__label" htmlFor={controlId}>
          {label}
        </label>
      ) : null}
    </span>
  );

  if (!hasFieldChrome) {
    return control;
  }

  return (
    <Field
      label={fieldLabel}
      labelPlacement={fieldLabel ? placement : 'none'}
      tip={tip}
      hint={hint}
      error={error}
      htmlFor={controlId}
      required={required}
      bindControlId={false}
      className={className}
    >
      {control}
    </Field>
  );
}

export default Checkbox;
