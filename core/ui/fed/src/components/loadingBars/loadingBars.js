import React from 'react';
import PropTypes from 'prop-types';
import './loadingBars.scss';

function LoadingBars({ barCount, className, 'aria-label': ariaLabel }) {
  const count = Math.max(3, Math.min(8, Number(barCount) || 5));
  const bars = Array.from({ length: count }, (_, i) => `bar-${i}`);

  return (
    <div
      className={['ntq-loading-bars', className].filter(Boolean).join(' ')}
      role="status"
      aria-label={ariaLabel || '加载中'}
    >
      {bars.map((key) => (
        <span key={key} className="ntq-loading-bars__bar" />
      ))}
    </div>
  );
}

LoadingBars.propTypes = {
  barCount: PropTypes.number,
  className: PropTypes.string,
  'aria-label': PropTypes.string,
};

LoadingBars.defaultProps = {
  barCount: 5,
  className: '',
  'aria-label': '加载中',
};

export default LoadingBars;
