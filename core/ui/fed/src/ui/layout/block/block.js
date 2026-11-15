import React from 'react';
import { RADIUS_TOKENS, SPACE_TOKENS, SURFACE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 块级容器原语。
 * padding / gap / radius / surface 只用语义 token。
 *
 * @example
 * <Block padding="md" gap="sm" surface="soft" radius="md" />
 * <Block surface="glass" radius="lg" bordered padding="md" />
 * <Block surface="panel" radius="none" padding="md" />
 */
function Block({
  padding = 'md',
  gap = 'none',
  radius,
  surface = 'none',
  bordered = false,
  className = '',
  style,
  children,
  ...rest
}) {
  const paddingToken = pickToken(padding, SPACE_TOKENS, 'md');
  const gapToken = pickToken(gap, SPACE_TOKENS, 'none');
  const surfaceToken = pickToken(surface, SURFACE_TOKENS, 'none');
  // 未传 radius：bordered 默认 md，否则 none；显式传 none 可无圆角
  const radiusToken = radius === undefined
    ? (bordered ? 'md' : 'none')
    : pickToken(radius, RADIUS_TOKENS, 'none');

  const rootClass = [
    'ntq-block',
    `ntq-block--pad-${paddingToken}`,
    `ntq-block--gap-${gapToken}`,
    `ntq-block--radius-${radiusToken}`,
    surfaceToken !== 'none' ? `ntq-block--surface-${surfaceToken}` : '',
    bordered ? 'ntq-block--bordered' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style} {...rest}>
      {children}
    </div>
  );
}

export default Block;
