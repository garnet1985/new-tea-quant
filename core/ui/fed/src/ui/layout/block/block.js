import React from 'react';
import { RADIUS_TOKENS, SPACE_TOKENS, resolveSurfaceToken } from 'ui/tokens';
import './style.scss';

/**
 * 块级容器原语。
 * padding / gap / radius / surface 只用语义 token。
 * 默认 gap="md"（1rem = --ntq-stack）；紧凑场景显式传 gap="none"。
 *
 * surface 三档：glass（透光）/ frost（毛玻璃）/ frost-strong（渐变毛玻璃）。
 * 旧名 soft→glass、panel→frost、gradient→frost-strong。
 *
 * @example
 * <Block surface="glass" radius="md" bordered />
 * <Block surface="frost" radius="lg" bordered />
 * <Block sticky surface="frost" radius="none">侧栏整栏贴顶</Block>
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
  const paddingToken = pickSpace(padding);
  const gapToken = pickSpace(gap);
  const surfaceToken = resolveSurfaceToken(surface);
  // 未传 radius：bordered 默认 md，否则 none；显式传 none 可无圆角
  const radiusToken = radius === undefined
    ? (bordered ? 'md' : 'none')
    : pickRadius(radius);

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

function pickSpace(value) {
  return SPACE_TOKENS.includes(value) ? value : 'md';
}

function pickRadius(value) {
  return RADIUS_TOKENS.includes(value) ? value : 'none';
}

export default Block;
