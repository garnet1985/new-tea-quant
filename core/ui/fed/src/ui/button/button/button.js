import React from 'react';
import { Button as MuiButton, Tooltip } from '@mui/material';
import Icon from 'ui/icon/icon';
import { ICON_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

const MUI_VARIANT = {
  glass: 'outlined',
  primary: 'contained',
  danger: 'contained',
  attention: 'outlined',
  ghost: 'text',
};

const SOLID_VARIANTS = new Set(['primary', 'danger']);

const ICON_PLACEMENTS = ['start', 'end'];
const EXTERNAL_LINK_ICON = 'chevronRight';

/** http(s) 外链，或显式 target=_blank：未指定 icon 时自动后置 chevronRight。 */
function isExternalLinkProps(href, target) {
  if (target === '_blank') return true;
  if (typeof href !== 'string' || !href) return false;
  return /^https?:\/\//i.test(href) || href.startsWith('//');
}

/**
 * 标准矩形按钮。基于 MUI Button。
 *
 * - icon + iconPlacement：前置 / 后置图标
 * - 仅 icon、无文案：纯图标按钮（需 aria-label 或 tooltip）
 * - tooltip：可选悬停说明
 * - href / component：可作按钮样式的超链接（外链或 RouterLink）
 * - 外链（http(s) 或 target=_blank）且未传 icon：自动后置 chevronRight
 *
 * CSS 根类暂仍为 `.ntq-button`（后续可改为 `ui-button`）。
 *
 * @example
 * <Button icon="add">添加</Button>
 * <Button icon="chevronRight" iconPlacement="end">下一步</Button>
 * <Button icon="settings" tooltip="设置" aria-label="设置" />
 * <Button href="/docs">文档</Button>
 */
/** 扩展：默认保持现有约 5px；传 none 为直角 */
const BUTTON_RADIUS_TOKENS = ['default', 'none'];

function Button({
  variant = 'glass',
  radius = 'default',
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
  const radiusToken = pickToken(radius, BUTTON_RADIUS_TOKENS, 'default');
  const hasLabel = children != null && children !== false && children !== '';
  const externalAutoIcon = !icon && hasLabel && isExternalLinkProps(rest.href, rest.target);
  const resolvedIcon = icon || (externalAutoIcon ? EXTERNAL_LINK_ICON : '');
  const placeToken = externalAutoIcon
    ? 'end'
    : (ICON_PLACEMENTS.includes(iconPlacement) ? iconPlacement : 'start');
  const iconOnly = Boolean(resolvedIcon) && !hasLabel;

  const iconEl = resolvedIcon
    ? (
      <Icon
        name={resolvedIcon}
        size={iconSizeToken}
        tone={SOLID_VARIANTS.has(variant) ? undefined : 'muted'}
      />
    )
    : null;

  const rootClass = [
    'ntq-button',
    `ntq-button--${MUI_VARIANT[variant] ? variant : 'glass'}`,
    radiusToken === 'none' ? 'ntq-button--radius-none' : '',
    iconOnly ? 'ntq-button--icon-only' : '',
    className,
  ].filter(Boolean).join(' ');

  const ariaLabel = rest['aria-label']
    || (iconOnly ? (tooltip || undefined) : undefined);

  const button = (
    <MuiButton
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
    </MuiButton>
  );

  if (!tooltip) {
    return button;
  }

  // disabled 时按钮不接收指针事件，需包一层才能显示 tooltip
  const trigger = disabled
    ? <span className="ntq-button__tooltip-wrap">{button}</span>
    : button;

  return (
    <Tooltip title={tooltip} arrow enterDelay={0} leaveDelay={0} describeChild>
      {trigger}
    </Tooltip>
  );
}

export default Button;
export { ICON_PLACEMENTS as BUTTON_ICON_PLACEMENTS };
