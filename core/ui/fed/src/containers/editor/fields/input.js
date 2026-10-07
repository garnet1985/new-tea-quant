import React from 'react';
import { TextField, Typography } from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';

function InputField({ field, value, errors, onChange, emitChangeMeta, context = {} }) {
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

  const helperBelow = fieldError
    || (field.description && !field.tooltip ? field.description : '')
    || '';

  return (
    <div key={field.name}>
      <EditorFieldLabel field={field} context={context} />
      <TextField
        size="small"
        type={field.type === 'number' ? 'number' : 'text'}
        multiline={Boolean(field.multiline)}
        minRows={field.multiline ? (field.minRows || 4) : undefined}
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
        placeholder={field.placeholder || ''}
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

export default InputField;
