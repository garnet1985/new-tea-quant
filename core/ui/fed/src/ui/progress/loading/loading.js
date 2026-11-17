import React from 'react';
import { LOADING_VARIANTS, pickToken } from 'ui/tokens';
import LoadingBars from 'ui/progress/loadingBars';
import './style.scss';

/**
 * 加载态组合：page / inline / inlineRow。
 */
function Loading({
  variant = 'inline',
  message = null,
  className = '',
  style,
  'aria-label': ariaLabel = '',
}) {
  const variantToken = pickToken(variant, LOADING_VARIANTS, 'inline');
  const barsSize = variantToken === 'page' ? 'md' : 'sm';
  const label = ariaLabel || (typeof message === 'string' ? message : '加载中');

  const rootClass = [
    'ntq-loading',
    `ntq-loading--${variantToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style} role="status" aria-label={label}>
      <LoadingBars size={barsSize} aria-label={label} />
      {message ? <p className="ntq-loading__message ntq-muted">{message}</p> : null}
    </div>
  );
}

export default Loading;
