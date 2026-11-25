import React from 'react';
import PropTypes from 'prop-types';
import RainbowButton from 'ntq-ui/rainbowButton';
import './style.scss';

function GlobalHelperButton({ onClick }) {
  return (
    <div className="ntq-global-helper__fab-slot">
      <RainbowButton
        size="lg"
        ring="still"
        mark="help"
        onClick={onClick}
        aria-label="打开页面引导"
      />
    </div>
  );
}

GlobalHelperButton.propTypes = {
  onClick: PropTypes.func,
};

export default GlobalHelperButton;
