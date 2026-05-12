import React from 'react';
import { MenuItem, Select, Typography } from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';

function SelectField({ field, value, onChange, emitChangeMeta }) {
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

  return (
    <div key={field.name}>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
        {field.label}
      </Typography>
      <Select
        size="small"
        fullWidth
        multiple={Boolean(field.multiple)}
        value={current ?? (field.multiple ? [] : '')}
        onChange={(e) => applyChange(e.target.value)}
        disabled={isReadonly}
      >
        {(field.options || []).map((item) => (
          <MenuItem key={item.value} value={item.value}>
            {item.label}
          </MenuItem>
        ))}
      </Select>
    </div>
  );
}

export default SelectField;