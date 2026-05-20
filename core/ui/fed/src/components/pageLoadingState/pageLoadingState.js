import React from 'react';
import PropTypes from 'prop-types';
import { Typography } from '@mui/material';
import LoadingBars from '../loadingBars/loadingBars';
import './pageLoadingState.scss';

function PageLoadingState({ message, className, minHeight, barCount }) {
  const style = minHeight ? { '--ntq-page-loading-min-height': minHeight } : undefined;

  return (
    <div
      className={['ntq-page-loading', className].filter(Boolean).join(' ')}
      style={style}
    >
      <LoadingBars barCount={barCount} />
      {message ? (
        <Typography variant="body2" component="p" className="ntq-page-loading__message">
          {message}
        </Typography>
      ) : null}
    </div>
  );
}

PageLoadingState.propTypes = {
  message: PropTypes.node,
  className: PropTypes.string,
  minHeight: PropTypes.string,
  barCount: PropTypes.number,
};

PageLoadingState.defaultProps = {
  message: null,
  className: '',
  minHeight: '',
  barCount: 5,
};

export default PageLoadingState;
