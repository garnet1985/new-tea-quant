import React from 'react';
import { Button } from '@mui/material';
import NtqIcon from 'ui/icon/ntqIcon';
import { ICON_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

const MUI_VARIANT = {
  glass: 'outlined',
  primary: 'contained',
  attention: 'outlined',
  ghost: 'text',
};

/**
 * NTQ 标准矩形按钮。基于 MUI Button，封装产品视觉变体。
 * iconSize 只用 sm|md|lg|xl。
 */
function NtqButton({
  variant = 'glass',
  icon = '',
  iconSize = 'md',
  className = '',
  children,
  ...rest
}) {
  const rootClass = ['ntq-button', `ntq-button--${variant}`, className].filter(Boolean).join(' ');
  const iconSizeToken = pickToken(iconSize, ICON_SIZE_TOKENS, 'md');
  const startIcon = icon
    ? <NtqIcon name={icon} size={iconSizeToken} tone={variant === 'primary' ? undefined : 'muted'} />
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
