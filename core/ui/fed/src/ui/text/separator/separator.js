import React from 'react';
import './style.scss';

/**
 * 分隔标题：左侧文案，右侧横线。
 * 用于小节标签（比 caption 更有分隔感）。
 *
 * @example
 * <Separator>行内特殊字形</Separator>
 * <Separator tone="muted">参数说明</Separator>
 */
function Separator({
  tone = 'default',
  className = '',
  children,
  ...rest
}) {
  const rootClass = [
    'ntq-separator',
    tone === 'muted' ? 'ntq-separator--muted' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} role="separator" {...rest}>
      <span className="ntq-separator__label">{children}</span>
      <span className="ntq-separator__line" aria-hidden="true" />
    </div>
  );
}

export default Separator;
