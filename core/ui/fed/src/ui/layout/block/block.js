import React from 'react';
import { RADIUS_TOKENS, SPACE_TOKENS, SURFACE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 块级容器原语。
 * padding / gap / radius / surface 只用语义 token。
 * 默认 gap="md"（1rem = --ntq-stack）；紧凑场景显式传 gap="none"。
 *
 * @example
 * <Block surface="soft" radius="md" bordered />
 * <Block surface="glass" radius="lg" bordered />
 * <Block surface="panel" radius="none" gap="none" />
 * <Block sticky surface="panel" radius="none">侧栏整栏贴顶</Block>
 */
function Block({
  padding = 'md',
  gap = 'md',
  radius,
  surface = 'none',
  bordered = false,
  sticky = false,
  className = '',
  style,
  children,
  ...rest
}) {
  const paddingToken = pickToken(padding, SPACE_TOKENS, 'md');
  const gapToken = pickToken(gap, SPACE_TOKENS, 'md');
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
    sticky ? 'ntq-block--sticky' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style} {...rest}>
      {children}
    </div>
  );
}

export default Block;
