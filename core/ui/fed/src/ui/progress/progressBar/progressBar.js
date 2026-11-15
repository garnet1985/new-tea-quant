import React from 'react';
import { PROGRESS_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 线性进度条。
 * value 为业务数据 0–100（不是样式数字）；尺寸用 size token。
 */
function ProgressBar({
  value = null,
  size = 'md',
  className = '',
  'aria-label': ariaLabel = '进度',
}) {
  const sizeToken = pickToken(size, PROGRESS_SIZE_TOKENS, 'md');
  const determinate = value != null && Number.isFinite(Number(value));
  const pct = determinate ? Math.max(0, Math.min(100, Number(value))) : null;

  const rootClass = [
    'ntq-progress-bar',
    `ntq-progress-bar--${sizeToken}`,
    determinate ? 'is-determinate' : 'is-indeterminate',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div
      className={rootClass}
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuemin={determinate ? 0 : undefined}
      aria-valuemax={determinate ? 100 : undefined}
      aria-valuenow={determinate ? pct : undefined}
    >
      <span
        className="ntq-progress-bar__fill"
        style={determinate ? { width: `${pct}%` } : undefined}
      />
    </div>
  );
}

export default ProgressBar;
