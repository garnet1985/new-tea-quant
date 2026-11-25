import React from 'react';
import { LOADING_BARS_SIZE_TOKENS, pickToken } from 'ui/tokens';
import './style.scss';

const BAR_KEYS = ['a', 'b', 'c', 'd', 'e'];

/**
 * 竖条加载指示。size 只选尺寸档；条数固定。
 */
function LoadingBars({
  size = 'md',
  className = '',
  'aria-label': ariaLabel = '加载中',
}) {
  const sizeToken = pickToken(size, LOADING_BARS_SIZE_TOKENS, 'md');
  const rootClass = [
    'ntq-loading-bars',
    `ntq-loading-bars--${sizeToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} role="status" aria-label={ariaLabel || '加载中'}>
      {BAR_KEYS.map((key) => (
        <span key={key} className="ntq-loading-bars__bar" />
      ))}
    </div>
  );
}

export default LoadingBars;
