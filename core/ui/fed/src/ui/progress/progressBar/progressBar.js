import React from 'react';
import { PROGRESS_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 线性进度条（回测风格：紫→青渐变）。
 * value 为业务数据 0–100；不传则为不确定进度。
 * label / showPercent 可选展示 step 名与百分比。
 *
 * @example
 * <ProgressBar value={42} />
 * <ProgressBar value={42} label="枚举信号" showPercent />
 * <ProgressBar size="sm" /> // indeterminate
 */
function ProgressBar({
  value = null,
  size = 'sm',
  label = null,
  showPercent = false,
  className = '',
  'aria-label': ariaLabel = '',
}) {
  const sizeToken = pickToken(size, PROGRESS_SIZE_TOKENS, 'sm');
  const determinate = value != null && Number.isFinite(Number(value));
  const pct = determinate ? Math.max(0, Math.min(100, Number(value))) : null;
  const rounded = determinate ? Math.round(pct) : null;
  const showMeta = Boolean(label) || (showPercent && determinate);
  const a11y = ariaLabel
    || (label && determinate ? `${label} ${rounded}%` : null)
    || (label || '进度');

  const rootClass = [
    'ntq-progress-bar',
    `ntq-progress-bar--${sizeToken}`,
    determinate ? 'is-determinate' : 'is-indeterminate',
    showMeta ? 'ntq-progress-bar--with-meta' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass}>
      {showMeta ? (
        <div className="ntq-progress-bar__meta">
          {label ? (
            <span className="ntq-progress-bar__label">{label}</span>
          ) : (
            <span className="ntq-progress-bar__label" />
          )}
          {showPercent && determinate ? (
            <span className="ntq-progress-bar__percent">{`${rounded}%`}</span>
          ) : null}
        </div>
      ) : null}
      <div
        className="ntq-progress-bar__track"
        role="progressbar"
        aria-label={a11y}
        aria-valuemin={determinate ? 0 : undefined}
        aria-valuemax={determinate ? 100 : undefined}
        aria-valuenow={determinate ? rounded : undefined}
      >
        <span
          className="ntq-progress-bar__fill"
          style={determinate ? { width: `${pct}%` } : undefined}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
