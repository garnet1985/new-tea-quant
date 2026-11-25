import React from 'react';
import { Switch as MuiSwitch } from '@mui/material';
import HelpTooltip from 'ui/message/helpTooltip';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import '../_control.scss';

/**
 * 开关。默认标签在左、开关在右（设置页常见）。
 * onChange 与 MUI 一致：e.target.checked。
 *
 * @example
 * <Switch label="启用实时扫描" checked={on} onChange={(e) => setOn(e.target.checked)} />
 * <Switch fieldLabel="通知" labelPlacement="above" tip="邮件" checked={on} onChange={…} />
 */
function Switch({
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
  const hasFieldChrome = Boolean(fieldLabel) || placement !== 'none' || hint || error;
  const { inputProps: restInputProps, ...switchRest } = rest;

  const switchNode = (
    <MuiSwitch
      name={name || undefined}
      size="small"
      checked={Boolean(checked)}
      onChange={onChange}
      disabled={disabled}
      inputProps={{
        id: controlId,
        'aria-label': label || fieldLabel || switchRest['aria-label'] || '开关',
        ...(restInputProps || {}),
      }}
      {...switchRest}
    />
  );

  // 无 Field 壳：左文案 + 右开关（可带 tip）
  if (!hasFieldChrome) {
    return (
      <span
        className={[
          'ntq-switch',
          disabled ? 'is-disabled' : '',
          className,
        ].filter(Boolean).join(' ')}
      >
        {(label || tip) ? (
          <span className="ntq-switch__text">
            {label ? (
              <label className="ntq-switch__label" htmlFor={controlId}>
                {label}
                {required ? <span aria-hidden="true"> *</span> : null}
              </label>
            ) : null}
            {tip ? <HelpTooltip title={tip} /> : null}
          </span>
        ) : null}
        {switchNode}
      </span>
    );
  }

  return (
    <Field
      label={fieldLabel || label}
      labelPlacement={placement === 'none' && fieldLabel ? 'above' : placement}
      tip={tip}
      hint={hint}
      error={error}
      htmlFor={controlId}
      required={required}
      bindControlId={false}
      className={className}
    >
      <span className={['ntq-switch', 'ntq-switch--control-only', disabled ? 'is-disabled' : ''].filter(Boolean).join(' ')}>
        {switchNode}
      </span>
    </Field>
  );
}

export default Switch;
