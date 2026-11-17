import React from 'react';
import PropTypes from 'prop-types';
import { LoadingBars } from 'ui';
import './style.scss';

function InlineLoadingState({
  message = null,
  compact = false,
  row = false,
  block = false,
  className = '',
  barCount = 5,
  'aria-label': ariaLabel = '',
}) {
  const rootClass = [
    'ntq-inline-loading',
    row ? 'is-row' : '',
    block ? 'ntq-inline-loading--block' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div
      className={rootClass}
      role="status"
      aria-label={ariaLabel || (typeof message === 'string' ? message : '加载中')}
    >
      <LoadingBars
        size={compact ? 'sm' : 'md'}
        aria-label={ariaLabel || (typeof message === 'string' ? message : '加载中')}
      />
      {message ? (
        <p
          className={[
            'ntq-inline-loading__message',
            compact ? 'ntq-inline-loading__message--compact' : '',
          ].filter(Boolean).join(' ')}
        >
          {message}
        </p>
      ) : null}
    </div>
  );
}

InlineLoadingState.propTypes = {
  message: PropTypes.node,
  compact: PropTypes.bool,
  row: PropTypes.bool,
  block: PropTypes.bool,
  className: PropTypes.string,
  barCount: PropTypes.number,
  'aria-label': PropTypes.string,
};

export default InlineLoadingState;
