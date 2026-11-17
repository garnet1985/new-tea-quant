import React from 'react';
import { SPACE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 纵向分区原语。默认 gap="md"（1rem = --ntq-stack）。
 * 块距只走 gap；子项不要再叠上下 margin。
 */
function Section({
  gap = 'md',
  className = '',
  style,
  children,
  ...rest
}) {
  const gapToken = pickToken(gap, SPACE_TOKENS, 'md');
  const rootClass = [
    'ntq-section',
    `ntq-section--gap-${gapToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <section className={rootClass} style={style} {...rest}>
      {children}
    </section>
  );
}

export default Section;
