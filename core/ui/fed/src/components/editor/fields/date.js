import React from 'react';
import { TextField, Typography } from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';

function DateField({ field, value, errors, onChange, emitChangeMeta, context = {} }) {
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

  const helperBelow = fieldError
    || (field.description && !field.tooltip ? field.description : '')
    || '';

  return (
    <div key={field.name}>
      <EditorFieldLabel field={field} context={context} />
      <TextField
        size="small"
        type="date"
        value={current || ''}
        fullWidth
        onChange={(e) => applyChange(e.target.value)}
        InputLabelProps={{ shrink: true }}
        InputProps={{ readOnly: isReadonly }}
        error={Boolean(fieldError)}
      />
      {helperBelow ? (
        <Typography
          variant="caption"
          color={fieldError ? 'error' : 'text.secondary'}
          sx={{ mt: 0.5, display: 'block' }}
        >
          {helperBelow}
        </Typography>
      ) : null}
    </div>
  );
}

export default DateField;
