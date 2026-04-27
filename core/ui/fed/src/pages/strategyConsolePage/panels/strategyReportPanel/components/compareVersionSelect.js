import React from 'react';
import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from '@mui/material';

function CompareVersionSelect({
  value,
  onChange,
  options = [],
  label = '选择对比版本',
  includeEmpty = true,
  emptyLabel = '不对比',
  minWidth = 220,
  maxWidth = 280,
}) {
  return (
    <FormControl size="small" sx={{ minWidth, maxWidth }}>
      <InputLabel id="compare-version-select-label">{label}</InputLabel>
      <Select
        labelId="compare-version-select-label"
        value={value}
        label={label}
        onChange={(event) => onChange(event.target.value)}
      >
        {includeEmpty ? <MenuItem value="">{emptyLabel}</MenuItem> : null}
        {options.map((option) => (
          <MenuItem key={option} value={option}>{option}</MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

export default CompareVersionSelect;
