import React from 'react';
import { SPACE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 纵向分区原语。gap 只用语义 token。
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
