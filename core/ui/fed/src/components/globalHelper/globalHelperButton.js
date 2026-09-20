import React from 'react';
import PropTypes from 'prop-types';
import { IconButton } from '@mui/material';

function GlobalHelperButton({ onClick }) {
  return (
    <div className="ntq-global-helper__fab-slot">
      <IconButton
        className="ntq-global-helper__fab"
        onClick={onClick}
        aria-label="打开页面引导"
        disableRipple
      >
        <span className="ntq-global-helper__fab-ring" aria-hidden />
        <span className="ntq-global-helper__fab-mark" aria-hidden>?</span>
      </IconButton>
    </div>
  );
}

GlobalHelperButton.propTypes = {
  onClick: PropTypes.func,
};

export default GlobalHelperButton;
