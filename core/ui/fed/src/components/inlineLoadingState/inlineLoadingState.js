import React from 'react';
import PropTypes from 'prop-types';
import { Typography } from '@mui/material';
import LoadingBars from '../loadingBars/loadingBars';
import './inlineLoadingState.scss';

function InlineLoadingState({
  message,
  compact,
  row,
  block,
  className,
  barCount,
  'aria-label': ariaLabel,
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
        barCount={barCount}
        className={compact ? 'ntq-loading-bars--sm' : ''}
        aria-label={ariaLabel || (typeof message === 'string' ? message : '加载中')}
      />
      {message ? (
        <Typography
          variant={compact ? 'caption' : 'body2'}
          component="p"
          className="ntq-inline-loading__message"
        >
          {message}
        </Typography>
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

InlineLoadingState.defaultProps = {
  message: null,
  compact: false,
  row: false,
  block: false,
  className: '',
  barCount: 5,
  'aria-label': '',
};

export default InlineLoadingState;
