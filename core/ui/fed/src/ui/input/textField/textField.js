import React from 'react';
import { TextField as MuiTextField } from '@mui/material';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import { inputChromeClass } from 'ui/input/controlChrome';
import '../_control.scss';

/**
 * 单行文本输入。标签布局走 Field。
 *
 * @example
 * <TextField label="名称" value={v} onChange={…} />
 * <TextField label="代码" labelPlacement="inline" />
 * <TextField maxWidth={false} /> // 去掉默认约 320px 上限
 * <TextField radius="none" /> // 直角
 * <TextField surface="glass" /> // 半透明玻璃
 */
function TextField({
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
  type = 'text',
  name = '',
  id = '',
  className = '',
  fullWidth = true,
  /** 默认限制约 320px；传 false 去掉上限 */
  maxWidth = true,
  /** 默认 solid 深色实底；glass=半透明 */
  surface = 'solid',
  /** 扩展：sm=默认圆角；none=直角 */
  radius = 'sm',
  ...rest
}) {
  const controlId = useControlId(id);
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const widthClass = maxWidth ? 'ntq-input--capped' : 'ntq-input--fluid';
  const chromeClass = inputChromeClass({ surface, radius });

  const control = (
    <MuiTextField
      id={controlId}
      name={name || undefined}
      size="small"
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      fullWidth={fullWidth}
      error={Boolean(error)}
      className={[
        'ntq-text-field',
        widthClass,
        chromeClass,
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      inputProps={{
        'aria-label': placement === 'none' ? (label || rest['aria-label'] || placeholder || '输入') : undefined,
      }}
      {...rest}
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

export default TextField;
