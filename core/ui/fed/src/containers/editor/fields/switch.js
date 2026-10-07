import React from 'react';
import {
  Stack,
  Switch,
} from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';

function SwitchField({ field, value, onChange, emitChangeMeta, context = {} }) {
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
    <Stack key={field.name} direction="row" justifyContent="space-between" alignItems="center">
      <EditorFieldLabel
        field={field}
        context={context}
        tooltipTitle={field.tooltip || field.description}
        sx={{ mb: 0 }}
      />
      <Switch size="small" checked={Boolean(current)} onChange={(e) => applyChange(e.target.checked)} disabled={isReadonly} />
    </Stack>
  );
}

export default SwitchField;