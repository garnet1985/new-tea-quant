import React from 'react';
import { Button, Tooltip } from '@mui/material';
import NtqIcon from 'ui/icon/ntqIcon';
import { ICON_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

const MUI_VARIANT = {
  glass: 'outlined',
  primary: 'contained',
  attention: 'outlined',
  ghost: 'text',
};

const ICON_PLACEMENTS = ['start', 'end'];

/**
 * NTQ 标准矩形按钮。基于 MUI Button。
 *
 * - icon + iconPlacement：前置 / 后置图标
 * - 仅 icon、无文案：纯图标按钮（需 aria-label 或 tooltip）
 * - tooltip：可选悬停说明
 * - href / component：可作按钮样式的超链接（外链或 RouterLink）
 *
 * @example
 * <NtqButton icon="add">添加</NtqButton>
 * <NtqButton icon="chevronRight" iconPlacement="end">下一步</NtqButton>
 * <NtqButton icon="settings" tooltip="设置" aria-label="设置" />
 * <NtqButton href="/docs">文档</NtqButton>
 */
function NtqButton({
  variant = 'glass',
  icon = '',
  iconSize = 'md',
  iconPlacement = 'start',
  tooltip = '',
  className = '',
  children,
  disabled = false,
  ...rest
}) {
  const iconSizeToken = pickToken(iconSize, ICON_SIZE_TOKENS, 'md');
  const placeToken = ICON_PLACEMENTS.includes(iconPlacement) ? iconPlacement : 'start';
  const hasLabel = children != null && children !== false && children !== '';
  const iconOnly = Boolean(icon) && !hasLabel;

  const iconEl = icon
    ? (
      <NtqIcon
        name={icon}
        size={iconSizeToken}
        tone={variant === 'primary' ? undefined : 'muted'}
      />
    )
    : null;

  const rootClass = [
    'ntq-button',
    `ntq-button--${variant}`,
    iconOnly ? 'ntq-button--icon-only' : '',
    className,
  ].filter(Boolean).join(' ');

  const ariaLabel = rest['aria-label']
    || (iconOnly ? (tooltip || undefined) : undefined);

  const button = (
    <Button
      {...rest}
      disabled={disabled}
      variant={MUI_VARIANT[variant] || 'outlined'}
      color={variant === 'primary' ? 'primary' : 'inherit'}
      startIcon={!iconOnly && placeToken === 'start' ? iconEl : undefined}
      endIcon={!iconOnly && placeToken === 'end' ? iconEl : undefined}
      className={rootClass}
      aria-label={ariaLabel}
    >
      {iconOnly ? iconEl : children}
    </Button>
  );

  if (!tooltip) {
    return button;
  }

  // disabled 时按钮不接收指针事件，需包一层才能显示 tooltip
  const trigger = disabled
    ? <span className="ntq-button__tooltip-wrap">{button}</span>
    : button;

  return (
    <Tooltip title={tooltip} arrow describeChild>
      {trigger}
    </Tooltip>
  );
}

export default NtqButton;
export { ICON_PLACEMENTS as NTQ_BUTTON_ICON_PLACEMENTS };
