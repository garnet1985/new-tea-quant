import React, { forwardRef } from 'react';
import { Chip } from '@mui/material';
import './style.scss';

const CountTab = forwardRef(function CountTab({
  label,
  count,
  selected = false,
  onClick,
  title,
  wide = false,
}, ref) {
  const hasCount = count != null && count !== '';
  const text = hasCount ? `${label} ${count}` : label;
  const rootClass = [
    'ntq-count-tab',
    wide ? 'ntq-count-tab--wide' : '',
    selected ? 'is-selected' : '',
  ].filter(Boolean).join(' ');
  return (
    <Chip
      ref={ref}
      size="small"
      clickable
      label={text}
      title={title}
      className={rootClass}
      aria-pressed={selected}
      onClick={onClick}
    />
  );
});

export default CountTab;
