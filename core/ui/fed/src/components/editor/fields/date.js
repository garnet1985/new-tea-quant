import React from 'react';
import { TextField } from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';

function DateField({ field, value, errors, onChange, emitChangeMeta }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = getByPath(value, field.name);
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
      type="date"
      label={field.label}
      value={current || ''}
      fullWidth
      onChange={(e) => applyChange(e.target.value)}
      InputLabelProps={{ shrink: true }}
      InputProps={{ readOnly: isReadonly }}
      error={Boolean(fieldError)}
      helperText={fieldError || field.description || ''}
    />
  );
}

export default DateField;