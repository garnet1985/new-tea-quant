import React from 'react';
import PropTypes from 'prop-types';
import { IconButton } from '@mui/material';
import './ntqRainbowRunButton.scss';

/**
 * 圆形彩虹描边运行钮（策略实验室执行步、Tag 列表等共用）。
 */
function NtqRainbowRunButton({
  done = false,
  disabled = false,
  onClick,
  ariaLabel = '运行',
  className = '',
}) {
  const glyphClass = done
    ? 'ntq-rainbow-run-btn__glyph--refresh'
    : 'ntq-rainbow-run-btn__glyph--play';

  return (
    <IconButton
      className={['ntq-rainbow-run-btn', className].filter(Boolean).join(' ')}
      disabled={disabled}
      onClick={onClick}
      aria-label={ariaLabel}
      disableRipple
    >
      <span className="ntq-rainbow-run-btn__ring" aria-hidden />
      <span className={`ntq-rainbow-run-btn__glyph ${glyphClass}`} aria-hidden>
        <span className="ntq-rainbow-run-btn__glyph-aurora" />
      </span>
    </IconButton>
  );
}

NtqRainbowRunButton.propTypes = {
  done: PropTypes.bool,
  disabled: PropTypes.bool,
  onClick: PropTypes.func,
  ariaLabel: PropTypes.string,
  className: PropTypes.string,
};

NtqRainbowRunButton.defaultProps = {
  done: false,
  disabled: false,
  onClick: undefined,
  ariaLabel: '运行',
  className: '',
};

export default NtqRainbowRunButton;
