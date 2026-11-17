import React, { forwardRef } from 'react';
import './style.scss';

/**
 * 带计数的筛选 Tab（Chip 形态）。
 * 用于列表上方「全部 / 归类」等过滤条；过滤逻辑由上层处理。
 *
 * @example
 * <CountTab label="全部" count={12} selected={!query} onClick={() => setQuery('')} wide />
 * <CountTab label="动量" count={3} selected={query === '动量'} onClick={() => setQuery('动量')} />
 */
const CountTab = forwardRef(function CountTab({
  label,
  count,
  selected = false,
  wide = false,
  disabled = false,
  title,
  className = '',
  onClick,
  ...rest
}, ref) {
  const hasCount = count != null && count !== '';
  const text = hasCount ? `${label} ${count}` : label;

  const rootClass = [
    'ntq-count-tab',
    wide ? 'ntq-count-tab--wide' : '',
    selected ? 'is-selected' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button
      {...rest}
      ref={ref}
      type="button"
      className={rootClass}
      title={title}
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
    >
      <span className="ntq-count-tab__label">{text}</span>
    </button>
  );
});

export default CountTab;
