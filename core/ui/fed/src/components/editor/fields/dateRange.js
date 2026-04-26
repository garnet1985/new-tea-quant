import React from 'react';
import { Box, TextField } from '@mui/material';
import { getByPath, setByPath } from '../editor.helper';

function DateRangeNode({ field, value, errors, onChange, emitChangeMeta }) {
  const startPath = field.startName;
  const endPath = field.endName;
  const startValue = getByPath(value, startPath) || '';
  const endValue = getByPath(value, endPath) || '';
  const startError = errors?.[startPath] || '';
  const endError = errors?.[endPath] || '';

  const apply = (nextStart, nextEnd, changedKey) => {
    if (!onChange) return;
    let updated = setByPath(value, startPath, nextStart || '');
    updated = setByPath(updated, endPath, nextEnd || '');

    const syncTargets = Array.isArray(field.syncTargets) ? field.syncTargets : [];
    syncTargets.forEach((target) => {
      if (!target?.startName || !target?.endName) return;
      updated = setByPath(updated, target.startName, nextStart || '');
      updated = setByPath(updated, target.endName, nextEnd || '');
    });

    onChange(updated);
    if (emitChangeMeta) {
      emitChangeMeta(updated, {
        name: field.name,
        value: { start: nextStart || '', end: nextEnd || '' },
        changedKey,
      });
    }
  };

  return (
    <Box
      key={field.name}
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
        gap: 1,
      }}
    >
      <TextField
        size="small"
        type="date"
        label={field.startLabel || 'From'}
        value={startValue}
        onChange={(e) => apply(e.target.value, endValue, 'start')}
        InputLabelProps={{ shrink: true }}
        error={Boolean(startError)}
        helperText={startError || ''}
      />
      <TextField
        size="small"
        type="date"
        label={field.endLabel || 'To'}
        value={endValue}
        onChange={(e) => apply(startValue, e.target.value, 'end')}
        InputLabelProps={{ shrink: true }}
        error={Boolean(endError)}
        helperText={endError || field.description || ''}
      />
    </Box>
  );
}

export default DateRangeNode;
