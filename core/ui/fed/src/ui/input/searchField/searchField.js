import React, { useState } from 'react';
import { InputAdornment, TextField as MuiTextField } from '@mui/material';
import Icon from 'ui/icon/icon';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import { inputChromeClass } from 'ui/input/controlChrome';
import '../_control.scss';

/**
 * 搜索输入：TextField + 前缀 search 图标。默认无字段标签（工具栏过滤）。
 * 不要与 TextField 合并——场景是列表/工具栏检索，不是普通表单短文本。
 *
 * @example
 * <SearchField value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索策略" />
 * <SearchField label="关键词" labelPlacement="above" tip="匹配名称" />
 */
function SearchField({
  label = '',
  labelPlacement = 'none',
  tip = '',
  hint = '',
  error = '',
  required = false,
  value,
  onChange,
  placeholder = '搜索',
  disabled = false,
  clearable = true,
  name = '',
  id = '',
  className = '',
  fullWidth = true,
  /** 默认约 360px；false 去掉上限 */
  maxWidth = true,
  /** 工具栏弹性宽度（ListToolbar 搜索槽常用） */
  fluid = false,
  surface = 'solid',
  radius = 'sm',
  ...rest
}) {
  const controlId = useControlId(id);
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'none');
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const widthClass = maxWidth ? 'ntq-input--search' : 'ntq-input--fluid';
  const chromeClass = inputChromeClass({ surface, radius });
  const [inner, setInner] = useState('');
  const controlled = value !== undefined;
  const current = controlled ? value : inner;

  const handleChange = (event) => {
    if (!controlled) setInner(event.target.value);
    if (typeof onChange === 'function') onChange(event);
  };

  const handleClear = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (disabled) return;
    const next = {
      target: {
        name: name || undefined,
        value: '',
      },
    };
    if (!controlled) setInner('');
    if (typeof onChange === 'function') onChange(next);
  };

  const showClear = clearable && String(current ?? '') !== '' && !disabled;

  const {
    InputProps: restInputProps,
    inputProps: restInputPropsInner,
    ...fieldRest
  } = rest;

  const control = (
    <MuiTextField
      id={controlId}
      name={name || undefined}
      size="small"
      value={current ?? ''}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      fullWidth={fullWidth}
      error={Boolean(error)}
      className={[
        'ntq-search-field',
        fluid ? 'ntq-search-field--fluid' : '',
        widthClass,
        chromeClass,
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      InputProps={{
        ...restInputProps,
        startAdornment: (
          <InputAdornment position="start" className="ntq-search-field__icon">
            <Icon name="search" size="sm" tone="muted" />
          </InputAdornment>
        ),
        endAdornment: showClear ? (
          <InputAdornment position="end">
            <button
              type="button"
              className="ntq-search-field__clear"
              aria-label="清除"
              onClick={handleClear}
              tabIndex={-1}
            >
              <Icon name="cancel" size="sm" tone="muted" />
            </button>
          </InputAdornment>
        ) : restInputProps?.endAdornment,
      }}
      inputProps={{
        'aria-label': placement === 'none'
          ? (label || fieldRest['aria-label'] || placeholder || '搜索')
          : undefined,
        ...restInputPropsInner,
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

export default SearchField;
