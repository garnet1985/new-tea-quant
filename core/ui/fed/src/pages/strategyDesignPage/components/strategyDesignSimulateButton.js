import React from 'react';
import PropTypes from 'prop-types';
import './strategyDesignSimulateButton.scss';

/**
 * 彩虹描边 + 渐变图标/文案的运行钮（形态来自策略实验室 ``ExecStepRunButton``，扩展为圆角矩形）。
 */
function StrategyDesignSimulateButton({
  done = false,
  disabled = false,
  onClick,
}) {
  const label = done ? '重新模拟' : '开始模拟';
  const glyphClass = done
    ? 'ntq-design-simulate-btn__glyph--refresh'
    : 'ntq-design-simulate-btn__glyph--play';

  return (
    <button
      type="button"
      className="ntq-design-simulate-btn"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
    >
      <span className="ntq-design-simulate-btn__aurora" aria-hidden />
      <span className="ntq-design-simulate-btn__inner">
        <span className={`ntq-design-simulate-btn__glyph ${glyphClass}`} aria-hidden>
          <span className="ntq-design-simulate-btn__glyph-aurora" />
        </span>
        <span className="ntq-design-simulate-btn__label-text">{label}</span>
      </span>
    </button>
  );
}

StrategyDesignSimulateButton.propTypes = {
  done: PropTypes.bool,
  disabled: PropTypes.bool,
  onClick: PropTypes.func,
};

StrategyDesignSimulateButton.defaultProps = {
  done: false,
  disabled: false,
  onClick: undefined,
};

export default StrategyDesignSimulateButton;
