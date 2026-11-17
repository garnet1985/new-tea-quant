import React from 'react';
import PropTypes from 'prop-types';
import { splitStrategyDescription } from '../../service/format/formatStrategyDescription';
import './style.scss';

/**
 * 策略说明多行文本。调用方用 className（如 ntq-muted）控色；maxLines 做行数截断。
 */
function StrategyDescriptionText({
  text = '',
  className = '',
  empty = '—',
  maxLines = null,
  component = 'div',
}) {
  const lines = splitStrategyDescription(text);
  const Tag = component || 'div';
  const clamped = maxLines != null && maxLines > 0;
  const rootClass = [
    'ntq-strategy-desc',
    clamped ? 'ntq-strategy-desc--clamp' : '',
    className,
  ].filter(Boolean).join(' ');
  const style = clamped
    ? { '--ntq-strategy-desc-lines': maxLines }
    : undefined;

  if (!lines.length) {
    if (empty == null || empty === '') return null;
    return (
      <Tag className={rootClass} style={style}>
        {empty}
      </Tag>
    );
  }

  if (clamped || lines.length === 1) {
    return (
      <Tag className={rootClass} style={style}>
        {lines.join('\n')}
      </Tag>
    );
  }

  return (
    <Tag className={rootClass}>
      {lines.map((line, idx) => (
        <p key={`${idx}-${line}`} className="ntq-strategy-desc__line">
          {line}
        </p>
      ))}
    </Tag>
  );
}

StrategyDescriptionText.propTypes = {
  text: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  className: PropTypes.string,
  empty: PropTypes.node,
  maxLines: PropTypes.number,
  component: PropTypes.elementType,
};

export default StrategyDescriptionText;
