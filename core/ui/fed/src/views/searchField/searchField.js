import React from 'react';
import { InputAdornment, TextField } from '@mui/material';
import NtqIcon from 'views/ntqIcon';
import './style.scss';

function SearchField({
  value,
  onChange,
  placeholder = '搜索',
  label = '搜索',
  fluid = false,
  className = '',
}) {
  const rootClass = ['ntq-search-field', fluid ? 'ntq-search-field--fluid' : '', className]
    .filter(Boolean)
    .join(' ');
  return (
    <TextField
      size="small"
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      inputProps={{ 'aria-label': label }}
      className={rootClass}
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <NtqIcon name="search" size={22} tone="muted" />
          </InputAdornment>
        ),
      }}
    />
  );
}

export default SearchField;
