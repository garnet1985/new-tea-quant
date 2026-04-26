import React from 'react';
import {
  Paper,
  Stack,
  Switch,
  Typography,
} from '@mui/material';
import Editor from '../../../components/editor/editor';
import FeesConfigEditor from './feesConfigEditor';
import strategyCapitalSimulatorSchema from '../editorSchemas/strategyCapitalSimulator';

function CapitalSimulatorSettingsEditor({ value, globalFees, onChange }) {
  const simulator = value || {};
  const overrideFees = Boolean(simulator.override_fees);

  const toggleOverrideFees = (enabled) => {
    if (!onChange) return;
    const next = { ...simulator };
    next.override_fees = enabled;
    if (enabled) {
      next.fees = next.fees && typeof next.fees === 'object'
        ? { ...next.fees }
        : { ...(globalFees || {}) };
    } else {
      delete next.fees;
    }
    onChange(next);
  };

  return (
    <Stack spacing={1}>
      <Editor
        schema={strategyCapitalSimulatorSchema}
        value={simulator}
        onChange={onChange}
      />

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
        {overrideFees ? (
          <FeesConfigEditor
            value={simulator.fees}
            onChange={(nextFees) => {
              if (!onChange) return;
              onChange({ ...simulator, fees: nextFees });
            }}
          />
        ) : null}
      </Paper>
    </Stack>
  );
}

export default CapitalSimulatorSettingsEditor;
