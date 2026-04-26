import React from 'react';
import {
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { getByPath, setByPath } from '../editor.helper';

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
    <Paper variant="outlined" sx={{ p: 1 }}>
      <Typography fontWeight={600} variant="body2" sx={{ mb: 1 }}>
        {field.label || '费用设置'}
      </Typography>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: enabled ? 1 : 0 }}>
        <Switch
          size="small"
          checked={enabled}
          onChange={(e) => toggleOverride(e.target.checked)}
        />
        <Typography variant="body2">{field.switchLabel || '覆盖全局费用'}</Typography>
      </Stack>

      {enabled ? (
        <Stack spacing={1}>
          {feeFields.map((feeField) => (
            <TextField
              key={feeField.name}
              size="small"
              type={feeField.type === 'number' ? 'number' : 'text'}
              label={feeField.label}
              value={getByPath(value, `${feesPath}.${feeField.name}`) ?? ''}
              fullWidth
              helperText={feeField.description || ''}
              onChange={(e) => setFeeValue(feeField.name, e.target.value, feeField)}
            />
          ))}
        </Stack>
      ) : null}
    </Paper>
  );
}

export default FeesOverrideField;
