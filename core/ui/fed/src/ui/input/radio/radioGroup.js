import React from 'react';
import { Radio, RadioGroup as MuiRadioGroup, FormControlLabel } from '@mui/material';
import Field from 'ui/input/field';
import useControlId from 'ui/input/useControlId';
import {
  FIELD_LABEL_PLACEMENTS,
  RADIO_DIRECTIONS,
  RADIO_VARIANTS,
  pickToken,
} from 'ui/tokens';
import '../_control.scss';

/**
 * 单选组。
 * variant="plain"：圆点；variant="button"：扫描页式大按钮卡片（可带 description）。
 *
 * @example
 * <RadioGroup label="频率" options={[…]} value={v} onChange={…} />
 * <RadioGroup
 *   variant="button"
 *   options={[
 *     { value: 'strict', label: '严格模式', description: '依赖最新交易日…' },
 *     { value: 'demo', label: '扫描演示', description: '演示用，非实时。' },
 *   ]}
 * />
 */
function RadioGroup({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  required = false,
  name = '',
  value,
  onChange,
  options = [],
  direction = 'column',
  variant = 'plain',
  disabled = false,
  className = '',
  ...rest
}) {
  const groupId = useControlId();
  const groupName = name || groupId;
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const variantToken = pickToken(variant, RADIO_VARIANTS, 'plain');
  const defaultDir = variantToken === 'button' ? 'row' : 'column';
  const dir = pickToken(direction, RADIO_DIRECTIONS, defaultDir);
  const list = Array.isArray(options) ? options : [];
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const current = value ?? '';

  const control = (
    <MuiRadioGroup
      id={groupId}
      name={groupName}
      value={current}
      onChange={onChange}
      className={[
        'ntq-radio-group',
        `ntq-radio-group--${variantToken}`,
        dir === 'row' ? 'ntq-radio-group--row' : '',
        disabled ? 'is-disabled' : '',
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      row={dir === 'row'}
      {...rest}
    >
      {list.map((opt) => {
        const optValue = opt?.value;
        const optLabel = opt?.label ?? String(optValue);
        const optDisabled = disabled || Boolean(opt?.disabled);
        const active = String(current) === String(optValue);
        const description = opt?.description;

        const labelNode = variantToken === 'button' ? (
          <span className="ntq-radio-group__card-body">
            <span className="ntq-radio-group__card-title">{optLabel}</span>
            {description ? (
              <span className="ntq-radio-group__card-desc">{description}</span>
            ) : null}
          </span>
        ) : (
          <span className="ntq-radio-group__label">{optLabel}</span>
        );

        return (
          <FormControlLabel
            key={String(optValue)}
            value={optValue}
            disabled={optDisabled}
            className={[
              'ntq-radio-group__option',
              variantToken === 'button' ? 'ntq-radio-group__option--button' : '',
              variantToken === 'button' && active ? 'is-active' : '',
              optDisabled ? 'is-disabled' : '',
            ].filter(Boolean).join(' ')}
            control={<Radio size="small" />}
            label={labelNode}
          />
        );
      })}
    </MuiRadioGroup>
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
      required={required}
      bindControlId={false}
      className={className}
    >
      {control}
    </Field>
  );
}

export default RadioGroup;
