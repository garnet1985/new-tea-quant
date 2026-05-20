import React from 'react';
import { MenuItem, Select, Typography } from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';

function SelectField({ field, value, onChange, emitChangeMeta, context = {} }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = getByPath(value, field.name);
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

  const options = field.options || [];
  const selectedOption = options.find((item) => item.value === current);
  const helperText = selectedOption?.tooltip
    || (field.description && !field.tooltip ? field.description : '');

  return (
    <div key={field.name}>
      <EditorFieldLabel field={field} context={context} />
      <Select
        size="small"
        fullWidth
        multiple={Boolean(field.multiple)}
        value={current ?? (field.multiple ? [] : '')}
        onChange={(e) => applyChange(e.target.value)}
        disabled={isReadonly}
        renderValue={(selected) => {
          const matched = options.find((item) => item.value === selected);
          return matched?.label ?? selected;
        }}
      >
        {options.map((item) => (
          <MenuItem
            key={item.value}
            value={item.value}
            title={item.tooltip || undefined}
          >
            {item.label}
          </MenuItem>
        ))}
      </Select>
      {helperText ? (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          {helperText}
        </Typography>
      ) : null}
    </div>
  );
}

export default SelectField;
