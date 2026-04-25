import React from 'react';
import {
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import FeesConfigEditor from './feesConfigEditor';

const ALLOCATION_MODES = ['equal_capital', 'equal_shares', 'kelly', 'custom'];

function isNonEmptyObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length > 0;
}

function toNumberOrEmpty(value) {
  if (value === '' || value === null || value === undefined) return '';
  const n = Number(value);
  return Number.isNaN(n) ? '' : n;
}

function CapitalSimulatorSettingsEditor({ value, globalFees, onChange }) {
  const simulator = value || {};
  const allocation = simulator.allocation || {};
  const mode = ALLOCATION_MODES.includes(allocation.mode) ? allocation.mode : 'equal_capital';
  const overrideFees = isNonEmptyObject(simulator.fees);

  const updateField = (key, nextValue) => {
    if (!onChange) return;
    onChange({
      ...simulator,
      [key]: nextValue,
    });
  };

  const updateAllocation = (key, nextValue) => {
    if (!onChange) return;
    onChange({
      ...simulator,
      allocation: {
        ...allocation,
        [key]: nextValue,
      },
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
      <TextField
        size="small"
        type="number"
        label="初始资金"
        value={simulator.initial_capital ?? ''}
        onChange={(e) => updateField('initial_capital', toNumberOrEmpty(e.target.value))}
        fullWidth
      />

      <Paper variant="outlined" sx={{ p: 1 }}>
        <Typography fontWeight={600} variant="body2" sx={{ mb: 1 }}>
          资金分配参数
        </Typography>
        <Stack spacing={1}>
          <TextField
            size="small"
            select
            label="分配模式"
            value={mode}
            onChange={(e) => updateAllocation('mode', e.target.value)}
            fullWidth
          >
            {ALLOCATION_MODES.map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
      </Paper>

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

export default CapitalSimulatorSettingsEditor;
