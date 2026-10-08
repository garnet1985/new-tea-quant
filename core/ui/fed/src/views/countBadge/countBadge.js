import React from 'react';
import './style.scss';

function CountBadge({ count, label }) {
  return (
    <span className="ntq-count-badge" aria-label={label}>
      {count}
    </span>
  );
}

export default CountBadge;
