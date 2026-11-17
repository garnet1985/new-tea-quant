import React from 'react';
import { PROGRESS_RING_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

const R = 15.5;
const C = 2 * Math.PI * R;

/**
 * 圆环进度（对齐回测 step 环：细描边、青色）。
 * value 0–100；不传为不确定旋转。label / showPercent 可选。
 * children 可覆盖环心内容（如步骤号）。
 *
 * @example
 * <ProgressRing value={65} showPercent />
 * <ProgressRing value={40} label="回测" showPercent />
 * <ProgressRing /> // indeterminate
 */
function ProgressRing({
  value = null,
  size = 'md',
  label = null,
  showPercent = false,
  children,
  className = '',
  'aria-label': ariaLabel = '',
}) {
  const sizeToken = pickToken(size, PROGRESS_RING_SIZE_TOKENS, 'md');
  const determinate = value != null && Number.isFinite(Number(value));
  const pct = determinate ? Math.max(0, Math.min(100, Number(value))) : null;
  const rounded = determinate ? Math.round(pct) : null;
  const a11y = ariaLabel
    || (label && determinate ? `${label} ${rounded}%` : null)
    || (label || '进度');

  let center = null;
  if (children != null && children !== false) {
    center = children;
  } else if (showPercent && determinate) {
    center = `${rounded}%`;
  }

  const rootClass = [
    'ntq-progress-ring',
    `ntq-progress-ring--${sizeToken}`,
    determinate ? 'is-determinate' : 'is-indeterminate',
    className,
  ].filter(Boolean).join(' ');

  const dashArray = determinate ? C : `${C * 0.28} ${C}`;
  const dashOffset = determinate ? C * (1 - pct / 100) : 0;

  return (
    <div
      className={rootClass}
      role="progressbar"
      aria-label={a11y}
      aria-valuemin={determinate ? 0 : undefined}
      aria-valuemax={determinate ? 100 : undefined}
      aria-valuenow={determinate ? rounded : undefined}
    >
      <div className="ntq-progress-ring__wrap">
        <svg
          className="ntq-progress-ring__svg"
          viewBox="0 0 36 36"
          aria-hidden="true"
        >
          <circle
            className="ntq-progress-ring__track"
            cx="18"
            cy="18"
            r={R}
            fill="none"
          />
          <circle
            className="ntq-progress-ring__fill"
            cx="18"
            cy="18"
            r={R}
            fill="none"
            strokeDasharray={dashArray}
            strokeDashoffset={dashOffset}
          />
        </svg>
        {center != null ? (
          <div className="ntq-progress-ring__center">{center}</div>
        ) : null}
      </div>
      {label ? (
        <div className="ntq-progress-ring__label">{label}</div>
      ) : null}
    </div>
  );
}

export default ProgressRing;
