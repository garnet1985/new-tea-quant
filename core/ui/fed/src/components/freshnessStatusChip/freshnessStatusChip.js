import React from 'react';
import { Chip, Tooltip } from '@mui/material';

/**
 * 数据源「数据状态」与 Tag「计算状态」共用 Chip 样式。
 * ``status``: ``up_to_date`` | ``needs_update`` | ``needs_recompute`` | …
 */
export default function FreshnessStatusChip({
  status = '',
  label = '—',
  hint = '',
  pending = false,
}) {
  const key = String(status || '').trim();
  let chip;
  if (pending) {
    chip = <Chip size="small" variant="outlined" label={label} />;
  } else if (key === 'up_to_date') {
    chip = <Chip size="small" color="success" variant="outlined" label={label} />;
  } else if (key === 'needs_update' || key === 'needs_recompute') {
    chip = <Chip size="small" color="warning" label={label} />;
  } else {
    chip = <Chip size="small" variant="outlined" label={label} />;
  }
  if (!hint || key === 'up_to_date' || pending) {
    return chip;
  }
  return (
    <Tooltip title={hint}>
      <span>{chip}</span>
    </Tooltip>
  );
}
