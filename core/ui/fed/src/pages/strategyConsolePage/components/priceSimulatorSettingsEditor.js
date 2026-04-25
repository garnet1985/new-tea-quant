import React from 'react';
import {
  Paper,
  Stack,
  Switch,
  Typography,
} from '@mui/material';
import FeesConfigEditor from './feesConfigEditor';

function isNonEmptyObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length > 0;
}

function PriceSimulatorSettingsEditor({ value, globalFees, onChange }) {
  const simulator = value || {};
  const overrideFees = isNonEmptyObject(simulator.fees);

  const updateField = (key, nextValue) => {
    if (!onChange) return;
    onChange({
      ...simulator,
      [key]: nextValue,
    });
  };

  const toggleOverrideFees = (enabled) => {
    if (!onChange) return;
    const next = { ...simulator };
    if (enabled) {
      next.fees = { ...(globalFees || {}) };
    } else {
      delete next.fees;
    }
    onChange(next);
  };

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Switch
          size="small"
          checked={Boolean(simulator.use_sampling)}
          onChange={(e) => updateField('use_sampling', e.target.checked)}
        />
        <Typography variant="body2">使用采样版本</Typography>
      </Stack>

      <Paper variant="outlined" sx={{ p: 1 }}>
        <Typography fontWeight={600} variant="body2" sx={{ mb: 1 }}>
          费用设置
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Switch
            size="small"
            checked={overrideFees}
            onChange={(e) => toggleOverrideFees(e.target.checked)}
          />
          <Typography variant="body2">覆盖全局费用</Typography>
        </Stack>
        <FeesConfigEditor
          value={overrideFees ? simulator.fees : globalFees}
          readonly={!overrideFees}
          onChange={(nextFees) => {
            if (!onChange || !overrideFees) return;
            onChange({ ...simulator, fees: nextFees });
          }}
        />
      </Paper>
    </Stack>
  );
}

export default PriceSimulatorSettingsEditor;
