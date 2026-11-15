import React from 'react';
import {
  HEADING_BAR_TOKENS,
  RADIUS_TOKENS,
  SPACE_TOKENS,
  SURFACE_TOKENS,
  pickToken,
} from 'ui/tokens';
import './style.scss';

/**
 * 说明性文本块（摘要、提示、反例说明等）。
 * 可带左侧竖条 + 可选表面；不是标题——标题用 Heading。
 *
 * @example
 * <TextBlock bar="cyan" surface="soft">组件用途说明…</TextBlock>
 * <TextBlock bar="warning" surface="soft"><ul>…</ul></TextBlock>
 */
function TextBlock({
  bar = 'cyan',
  surface = 'soft',
  radius = 'md',
  padding = 'md',
  className = '',
  style,
  children,
  ...rest
}) {
  const barToken = HEADING_BAR_TOKENS.includes(bar) ? bar : 'cyan';
  const surfaceToken = pickToken(surface, SURFACE_TOKENS, 'soft');
  const radiusToken = pickToken(radius, RADIUS_TOKENS, 'md');
  const paddingToken = pickToken(padding, SPACE_TOKENS, 'md');

  const rootClass = [
    'ntq-text-block',
    `ntq-text-block--bar-${barToken}`,
    surfaceToken !== 'none' ? `ntq-text-block--surface-${surfaceToken}` : '',
    `ntq-text-block--radius-${radiusToken}`,
    `ntq-text-block--pad-${paddingToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style} {...rest}>
      <div className="ntq-text-block__body">{children}</div>
    </div>
  );
}

export default TextBlock;
