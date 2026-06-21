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
  runLabel = '开始模拟',
  rerunLabel = '重新模拟',
  compact = false,
  className = '',
}) {
  const label = done ? rerunLabel : runLabel;
  const glyphClass = done
    ? 'ntq-design-simulate-btn__glyph--refresh'
    : 'ntq-design-simulate-btn__glyph--play';
  const rootClass = [
    'ntq-design-simulate-btn',
    compact ? 'ntq-design-simulate-btn--compact' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button
      type="button"
      className={rootClass}
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
  runLabel: PropTypes.string,
  rerunLabel: PropTypes.string,
  compact: PropTypes.bool,
  className: PropTypes.string,
};

StrategyDesignSimulateButton.defaultProps = {
  done: false,
  disabled: false,
  onClick: undefined,
  runLabel: '开始模拟',
  rerunLabel: '重新模拟',
  compact: false,
  className: '',
};

export default StrategyDesignSimulateButton;
