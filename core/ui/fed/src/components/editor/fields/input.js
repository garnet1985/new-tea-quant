import React from 'react';
import { TextField } from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';

function InputField({ field, value, errors, onChange, emitChangeMeta }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = getByPath(value, field.name);
  const uiValue = typeof field.format === 'function'
    ? field.format(current, value)
    : (current ?? '');
  const fieldError = errors?.[field.name] || '';
  const isReadonly = typeof field?.readonlyWhen === 'function'
    ? Boolean(field.readonlyWhen({ values: value }))
    : Boolean(field?.readonly);

  const applyChange = (next) => {
    if (!onChange) return;
    let updated = setByPath(value, field.name, next);
    updated = runFieldEvents(updated, field, next);
    onChange(updated);
    if (emitChangeMeta) {
      emitChangeMeta(updated, { name: field.name, value: next });
    }
  };

  return (
    <TextField
      key={field.name}
      size="small"
      type={field.type === 'number' ? 'number' : 'text'}
      multiline={Boolean(field.multiline)}
      minRows={field.multiline ? (field.minRows || 4) : undefined}
      label={field.label}
      value={uiValue}
      fullWidth
      error={Boolean(fieldError)}
      onChange={(e) => {
        if (typeof field.parse === 'function') {
          applyChange(field.parse(e.target.value, value));
          return;
        }
        if (field.type === 'number') {
          const raw = e.target.value;
          if (raw === '') {
            applyChange('');
            return;
          }
          const n = Number(raw);
          applyChange(Number.isNaN(n) ? '' : n);
          return;
        }
        applyChange(e.target.value);
      }}
      InputProps={{ readOnly: isReadonly }}
      helperText={fieldError || field.description || ''}
    />
  );
}

export default InputField;