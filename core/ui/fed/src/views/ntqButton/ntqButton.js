import React from 'react';
import { Button } from '@mui/material';
import NtqIcon from 'views/ntqIcon';
import './style.scss';

const MUI_VARIANT = {
  glass: 'outlined',
  primary: 'contained',
  attention: 'outlined',
  ghost: 'text',
};

function NtqButton({
  variant = 'glass',
  icon = '',
  iconSize = 22,
  className = '',
  children,
  ...rest
}) {
  const rootClass = ['ntq-button', `ntq-button--${variant}`, className].filter(Boolean).join(' ');
  const startIcon = icon
    ? <NtqIcon name={icon} size={iconSize} tone={variant === 'primary' ? undefined : 'muted'} />
    : undefined;
  return (
    <Button
      {...rest}
      variant={MUI_VARIANT[variant] || 'outlined'}
      color={variant === 'primary' ? 'primary' : 'inherit'}
      startIcon={startIcon}
      className={rootClass}
    >
      {children}
    </Button>
  );
}

export default NtqButton;
