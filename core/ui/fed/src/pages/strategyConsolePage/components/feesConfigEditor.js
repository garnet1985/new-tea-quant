import React from 'react';
import { Stack, TextField } from '@mui/material';

function toNumberOrEmpty(value) {
  if (value === '' || value === null || value === undefined) return '';
  const n = Number(value);
  return Number.isNaN(n) ? '' : n;
}

function FeesConfigEditor({ value, onChange, readonly = false }) {
  const fees = value || {};

  const updateField = (key, nextValue) => {
    if (!onChange || readonly) return;
    onChange({
      ...fees,
      [key]: toNumberOrEmpty(nextValue),
    });
  };

  return (
    <Stack spacing={1}>
      <TextField
        size="small"
        type="number"
        label="佣金率 (commission_rate)"
        value={fees.commission_rate ?? ''}
        onChange={(e) => updateField('commission_rate', e.target.value)}
        fullWidth
        InputProps={{ readOnly: readonly }}
      />
      <TextField
        size="small"
        type="number"
        label="最低佣金 (min_commission)"
        value={fees.min_commission ?? ''}
        onChange={(e) => updateField('min_commission', e.target.value)}
        fullWidth
        InputProps={{ readOnly: readonly }}
      />
      <TextField
        size="small"
        type="number"
        label="印花税率 (stamp_duty_rate)"
        value={fees.stamp_duty_rate ?? ''}
        onChange={(e) => updateField('stamp_duty_rate', e.target.value)}
        fullWidth
        InputProps={{ readOnly: readonly }}
      />
      <TextField
        size="small"
        type="number"
        label="过户费率 (transfer_fee_rate)"
        value={fees.transfer_fee_rate ?? ''}
        onChange={(e) => updateField('transfer_fee_rate', e.target.value)}
        fullWidth
        InputProps={{ readOnly: readonly }}
      />
    </Stack>
  );
}

export default FeesConfigEditor;
