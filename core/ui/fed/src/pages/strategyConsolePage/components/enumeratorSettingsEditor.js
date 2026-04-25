import React from 'react';
import { Stack, Switch, Typography } from '@mui/material';

function EnumeratorSettingsEditor({ value, onChange }) {
  const enumerator = value || {};

  const updateField = (key, nextValue) => {
    if (!onChange) return;
    onChange({
      ...enumerator,
      [key]: nextValue,
    });
  };

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Switch
          size="small"
          checked={Boolean(enumerator.use_sampling)}
          onChange={(e) => updateField('use_sampling', e.target.checked)}
        />
        <Typography variant="body2">使用采样枚举</Typography>
      </Stack>
    </Stack>
  );
}

export default EnumeratorSettingsEditor;
