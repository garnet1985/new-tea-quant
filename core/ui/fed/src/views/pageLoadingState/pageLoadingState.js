import React from 'react';
import PropTypes from 'prop-types';
import { LoadingBars } from 'ui';
import './style.scss';

function PageLoadingState({ message = null, className = '', minHeight = '', barCount = 5 }) {
  const style = minHeight ? { '--ntq-page-loading-min-height': minHeight } : undefined;

  return (
    <div
      className={['ntq-page-loading', className].filter(Boolean).join(' ')}
      style={style}
    >
      <LoadingBars size="md" />
      {message ? (
        <p className="ntq-page-loading__message">{message}</p>
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

export default PageLoadingState;
