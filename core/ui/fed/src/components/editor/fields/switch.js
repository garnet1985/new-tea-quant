import React from 'react';
import NtqHelpTooltip from '../../ntqHelpTooltip/ntqHelpTooltip';
import {
  Stack,
  Switch,
  Typography,
} from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';

function SwitchField({ field, value, onChange, emitChangeMeta }) {
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
      <Stack direction="row" spacing={0.5} alignItems="center">
        <Typography variant="body2">{field.label}</Typography>
        {field.description ? (
          <NtqHelpTooltip title={field.description} />
        ) : null}
      </Stack>
      <Switch size="small" checked={Boolean(current)} onChange={(e) => applyChange(e.target.checked)} disabled={isReadonly} />
    </Stack>
  );
}

export default SwitchField;