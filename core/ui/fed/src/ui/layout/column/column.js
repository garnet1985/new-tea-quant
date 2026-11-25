import React from 'react';
import {
  ALIGN_TOKENS,
  COLUMN_VARIANTS,
  DIVIDER_TOKENS,
  SPACE_TOKENS,
  pickToken,
} from 'ui/tokens';
import './style.scss';

/**
 * 分栏布局原语。
 * variant 描述版式；gap / align / divider 用语义 token。
 *
 * @example
 * <Column variant="thirds" gap="md">...</Column>
 * <Column variant="sidebar" gap="none" divider="line">...</Column>
 */
function Column({
  variant = 'halves',
  gap = 'md',
  align = 'stretch',
  divider = 'none',
  stack = true,
  className = '',
  style,
  children,
  ...rest
}) {
  const variantToken = pickToken(variant, COLUMN_VARIANTS, 'halves');
  const gapToken = pickToken(gap, SPACE_TOKENS, 'md');
  const alignToken = pickToken(align, ALIGN_TOKENS, 'stretch');
  const dividerToken = pickToken(divider, DIVIDER_TOKENS, 'none');

  const rootClass = [
    'ntq-column',
    `ntq-column--${variantToken}`,
    `ntq-column--gap-${gapToken}`,
    `ntq-column--align-${alignToken}`,
    dividerToken !== 'none' ? `ntq-column--divider-${dividerToken}` : '',
    stack ? '' : 'ntq-column--no-stack',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style} {...rest}>
      {children}
    </div>
  );
}

export default Column;
export { COLUMN_VARIANTS };
