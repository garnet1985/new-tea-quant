import React from 'react';
import './style.scss';

/**
 * 圆形计数角标（如列表行内数量）。
 *
 * @example
 * <CountBadge count={3} label="信号数" />
 */
function CountBadge({
  count,
  label,
  className = '',
  ...rest
}) {
  const rootClass = ['ntq-count-badge', className].filter(Boolean).join(' ');
  return (
    <span
      className={rootClass}
      aria-label={label}
      {...rest}
    >
      {count}
    </span>
  );
}

export default CountBadge;
