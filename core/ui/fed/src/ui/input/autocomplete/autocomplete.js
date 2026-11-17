import React, { useMemo } from 'react';
import {
  Autocomplete as MuiAutocomplete,
  TextField as MuiTextField,
} from '@mui/material';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import '../_control.scss';

function emitChange(onChange, name, next) {
  if (typeof onChange !== 'function') return;
  onChange({
    target: {
      name: name || undefined,
      value: next,
    },
  });
}

function optionValue(opt) {
  if (opt === null || opt === undefined) return '';
  if (typeof opt === 'string' || typeof opt === 'number') return opt;
  return opt.value;
}

function optionLabel(opt) {
  if (opt === null || opt === undefined) return '';
  if (typeof opt === 'string' || typeof opt === 'number') return String(opt);
  return opt.label ?? String(opt.value ?? '');
}

/**
 * 自动完成：可输入过滤 + 从建议中选择（可多选）。
 * 与 SearchSelect 不同：输入框即过滤/展示；与 TextField 不同：带建议列表。
 * onChange 与 Select 对齐：e.target.value（多选为 value 数组）。
 *
 * @example
 * <Autocomplete
 *   label="执行单元"
 *   options={[{ value: 'a', label: '单元 A' }]}
 *   value={v}
 *   onChange={(e) => setV(e.target.value)}
 * />
 */
function Autocomplete({
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
  placeholder = '输入或选择',
  disabled = false,
  multiple = false,
  clearable = true,
  noOptionsText = '无匹配项',
  className = '',
  fullWidth = true,
  /** 默认约 280px；false 去掉上限 */
  maxWidth = true,
  ...rest
}) {
  const controlId = useControlId(id);
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const list = useMemo(() => (Array.isArray(options) ? options : []), [options]);
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const widthClass = maxWidth ? 'ntq-input--capped' : 'ntq-input--fluid';

  const selected = useMemo(() => {
    if (multiple) {
      const arr = Array.isArray(value) ? value : [];
      return arr
        .map((v) => list.find((o) => String(optionValue(o)) === String(v)))
        .filter(Boolean);
    }
    if (value === '' || value === null || value === undefined) return null;
    return list.find((o) => String(optionValue(o)) === String(value)) || null;
  }, [list, multiple, value]);

  const {
    componentsProps: restComponentsProps,
    ListboxProps: restListboxProps,
    ...autoRest
  } = rest;

  const control = (
    <MuiAutocomplete
      id={controlId}
      options={list}
      value={selected}
      multiple={multiple}
      disabled={disabled}
      disableClearable={!clearable}
      noOptionsText={noOptionsText}
      getOptionLabel={optionLabel}
      isOptionEqualToValue={(a, b) => String(optionValue(a)) === String(optionValue(b))}
      getOptionDisabled={(opt) => Boolean(opt?.disabled)}
      onChange={(_, next) => {
        if (multiple) {
          const arr = Array.isArray(next) ? next : [];
          emitChange(onChange, name, arr.map(optionValue));
          return;
        }
        emitChange(onChange, name, next == null ? '' : optionValue(next));
      }}
      className={[
        'ntq-autocomplete',
        widthClass,
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      fullWidth={fullWidth}
      ListboxProps={{
        className: [
          'ntq-autocomplete__listbox',
          restListboxProps?.className,
        ].filter(Boolean).join(' '),
        ...restListboxProps,
      }}
      componentsProps={{
        ...restComponentsProps,
        paper: {
          className: [
            'ntq-autocomplete__paper',
            restComponentsProps?.paper?.className,
          ].filter(Boolean).join(' '),
          ...restComponentsProps?.paper,
        },
      }}
      renderInput={(params) => (
        <MuiTextField
          {...params}
          name={name || undefined}
          size="small"
          placeholder={placeholder}
          error={Boolean(error)}
          inputProps={{
            ...params.inputProps,
            'aria-label': placement === 'none'
              ? (label || autoRest['aria-label'] || placeholder || '自动完成')
              : params.inputProps?.['aria-label'],
          }}
        />
      )}
      {...autoRest}
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

export default Autocomplete;
