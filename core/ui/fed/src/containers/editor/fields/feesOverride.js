import React from 'react';
import { Switch, TextField } from 'ui';
import { getByPath, setByPath } from '../editor.helper';
import './style.scss';

function parseWithField(field, raw) {
  if (typeof field?.parse === 'function') return field.parse(raw);
  if (field?.type === 'number') {
    if (raw === '' || raw === null || raw === undefined) return '';
    const n = Number(raw);
    return Number.isNaN(n) ? '' : n;
  }
  return raw;
}

function FeesOverrideField({ field, value, onChange, emitChangeMeta }) {
  const enabled = Boolean(getByPath(value, field.flagName || 'override_fees'));
  const feesPath = field.feesName || 'fees';
  const feeFields = Array.isArray(field.feeFields) ? field.feeFields : [];

  const emit = (nextValue, meta) => {
    if (!onChange) return;
    onChange(nextValue);
    if (emitChangeMeta) emitChangeMeta(nextValue, meta);
  };

  const toggleOverride = (nextEnabled) => {
    let updated = setByPath(value, field.flagName || 'override_fees', nextEnabled);
    if (nextEnabled) {
      const currentFees = getByPath(updated, feesPath);
      if (!currentFees || typeof currentFees !== 'object') {
        updated = setByPath(updated, feesPath, {});
      }
    } else {
      updated = setByPath(updated, feesPath, undefined);
      const parts = String(feesPath).split('.');
      if (parts.length === 1) {
        const cloned = { ...(updated || {}) };
        delete cloned[feesPath];
        updated = cloned;
      }
    }
    emit(updated, { name: field.name, value: nextEnabled, changedKey: 'override_fees' });
  };

  const setFeeValue = (feeName, rawValue, feeField) => {
    const nextFeeValue = parseWithField(feeField, rawValue);
    let updated = setByPath(value, field.flagName || 'override_fees', true);
    updated = setByPath(updated, `${feesPath}.${feeName}`, nextFeeValue);
    emit(updated, { name: `${feesPath}.${feeName}`, value: nextFeeValue });
  };

  return (
    <div className="ntq-editor-fees-override">
      <p className="ntq-editor-fees-override__title">
        {field.label || '费用设置'}
      </p>
      <div
        className={[
          'ntq-editor-fees-override__switch',
          enabled ? 'ntq-editor-fees-override__switch--open' : '',
        ].filter(Boolean).join(' ')}
      >
        <Switch
          label={field.switchLabel || '覆盖全局费用'}
          checked={enabled}
          onChange={(e) => toggleOverride(e.target.checked)}
        />
      </div>

      {enabled ? (
        <div className="ntq-editor-fees-override__fields">
          {feeFields.map((feeField) => (
            <TextField
              key={feeField.name}
              maxWidth={false}
              type={feeField.type === 'number' ? 'number' : 'text'}
              label={feeField.label}
              hint={feeField.description || ''}
              value={getByPath(value, `${feesPath}.${feeField.name}`) ?? ''}
              onChange={(e) => setFeeValue(feeField.name, e.target.value, feeField)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default FeesOverrideField;
