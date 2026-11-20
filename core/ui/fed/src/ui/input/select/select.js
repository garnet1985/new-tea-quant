import React from 'react';
import { FormControl, MenuItem, Select as MuiSelect } from '@mui/material';
import Field from 'ui/input/field';
import InstantTransition from 'ui/input/instantTransition';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import { inputChromeClass } from 'ui/input/controlChrome';
import '../_control.scss';

/**
 * 基础下拉。options: { value, label, disabled? }[]。
 * onChange 与原生/MUI 一致：e.target.value。
 *
 * @example
 * <Select
 *   label="周期"
 *   value={v}
 *   onChange={(e) => setV(e.target.value)}
 *   options={[{ value: 'd', label: '日' }, { value: 'w', label: '周' }]}
 * />
 */
function Select({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  required = false,
  name = '',
  id = '',
  value,
  onChange,
  options = [],
  placeholder = '请选择',
  disabled = false,
  multiple = false,
  displayEmpty = true,
  className = '',
  fullWidth = true,
  /** 默认限制约 320px；传 false 去掉上限 */
  maxWidth = true,
  surface = 'solid',
  radius = 'sm',
  ...rest
}) {
  const controlId = useControlId(id);
  const labelId = `${controlId}-label`;
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const list = Array.isArray(options) ? options : [];
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  // 必填时不允许空值：不下发「请选择」项，也避免把空串当成合法选中值展示。
  const allowEmpty = !required && displayEmpty;
  const empty = multiple ? [] : '';
  let current = value === undefined || value === null ? empty : value;
  if (!multiple && required && (current === '' || current === null || current === undefined) && list.length > 0) {
    const firstEnabled = list.find((opt) => !opt.disabled) || list[0];
    current = firstEnabled?.value ?? empty;
  }
  const widthClass = maxWidth ? 'ntq-input--capped' : 'ntq-input--fluid';
  const chromeClass = inputChromeClass({ surface, radius });

  const renderValue = (selected) => {
    if (multiple) {
      const arr = Array.isArray(selected) ? selected : [];
      if (!arr.length) {
        return <span className="ntq-select__placeholder">{placeholder}</span>;
      }
      return arr
        .map((v) => list.find((o) => String(o.value) === String(v))?.label ?? v)
        .join('、');
    }
    if (selected === '' || selected === null || selected === undefined) {
      return <span className="ntq-select__placeholder">{placeholder}</span>;
    }
    const matched = list.find((o) => String(o.value) === String(selected));
    return matched?.label ?? selected;
  };

  const { MenuProps: restMenuProps, inputProps: restInputProps, ...selectRest } = rest;

  const control = (
    <FormControl
      fullWidth={fullWidth}
      size="small"
      error={Boolean(error)}
      disabled={disabled}
      className={[
        'ntq-select',
        widthClass,
        chromeClass,
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
    >
      <MuiSelect
        // combobox 是 div，不能用 label[for]；用 labelId + aria-labelledby
        labelId={hasFieldChrome && placement !== 'none' ? labelId : undefined}
        name={name || undefined}
        value={current}
        onChange={onChange}
        multiple={multiple}
        displayEmpty={displayEmpty}
        renderValue={renderValue}
        inputProps={{
          'aria-label': placement === 'none'
            ? (label || selectRest['aria-label'] || placeholder || '选择')
            : undefined,
          ...(restInputProps || {}),
        }}
        MenuProps={{
          disableScrollLock: true,
          variant: 'menu',
          TransitionComponent: InstantTransition,
          transitionDuration: 0,
          anchorOrigin: { vertical: 'bottom', horizontal: 'left' },
          transformOrigin: { vertical: 'top', horizontal: 'left' },
          ...(restMenuProps || {}),
          BackdropProps: {
            className: 'ntq-menu-backdrop',
            invisible: true,
            ...(restMenuProps?.BackdropProps || {}),
          },
          PaperProps: {
            className: [
              'ntq-select__paper',
              restMenuProps?.PaperProps?.className,
            ].filter(Boolean).join(' '),
            ...(restMenuProps?.PaperProps || {}),
          },
        }}
        {...selectRest}
      >
        {!multiple && allowEmpty ? (
          <MenuItem value="">
            <span className="ntq-select__placeholder">{placeholder}</span>
          </MenuItem>
        ) : null}
        {list.map((opt) => (
          <MenuItem
            key={String(opt.value)}
            value={opt.value}
            disabled={Boolean(opt.disabled)}
          >
            {opt.label ?? String(opt.value)}
          </MenuItem>
        ))}
      </MuiSelect>
    </FormControl>
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
      htmlFor={false}
      labelId={labelId}
      required={required}
      bindControlId={false}
      className={[widthClass, className].filter(Boolean).join(' ')}
    >
      {control}
    </Field>
  );
}

export default Select;
