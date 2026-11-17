import React from 'react';
import './style.scss';

/**
 * Pro 彩虹描边小徽章（会员条等复用）。
 */
function ProBadge({
  children = 'Pro',
  className = '',
  ...rest
}) {
  const rootClass = ['ntq-pro-badge', className].filter(Boolean).join(' ');
  return (
    <span className={rootClass} aria-label="Pro" {...rest}>
      {children}
    </span>
  );
}

export default ProBadge;
