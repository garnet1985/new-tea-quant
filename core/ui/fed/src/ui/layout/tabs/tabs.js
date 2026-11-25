import React, { useId, useMemo, useState } from 'react';
import { SPACE_TOKENS, TABS_VARIANTS, pickToken } from 'ui/tokens';
import './style.scss';

/**
 * 布局 Tab：上方切换（top）或左右分栏（side）。
 *
 * @example
 * <Tabs
 *   variant="top"
 *   items={[
 *     { id: 'a', label: '概览', content: <p>A</p> },
 *     { id: 'b', label: '详情', content: <p>B</p> },
 *   ]}
 * />
 * <Tabs variant="side" defaultValue="a" items={...} />
 */
function Tabs({
  variant = 'top',
  items = [],
  value,
  defaultValue = '',
  onChange,
  gap = 'md',
  className = '',
  style,
  ...rest
}) {
  const variantToken = pickToken(variant, TABS_VARIANTS, 'top');
  const gapToken = pickToken(gap, SPACE_TOKENS, 'md');
  const reactId = useId();
  const baseId = `ntq-tabs-${reactId.replace(/:/g, '')}`;

  const firstId = items[0]?.id || '';
  const isControlled = value !== undefined && value !== null;
  const [innerValue, setInnerValue] = useState(defaultValue || firstId);
  const activeId = isControlled ? value : innerValue;

  const activeItem = useMemo(
    () => items.find((item) => item.id === activeId) || items[0] || null,
    [items, activeId],
  );

  const select = (id) => {
    if (!isControlled) setInnerValue(id);
    if (typeof onChange === 'function') onChange(id);
  };

  const rootClass = [
    'ntq-tabs',
    `ntq-tabs--${variantToken}`,
    `ntq-tabs--gap-${gapToken}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} style={style} {...rest}>
      <div
        className="ntq-tabs__list"
        role="tablist"
        aria-orientation={variantToken === 'side' ? 'vertical' : 'horizontal'}
      >
        {items.map((item) => {
          const selected = activeItem && item.id === activeItem.id;
          const tabId = `${baseId}-tab-${item.id}`;
          const panelId = `${baseId}-panel-${item.id}`;
          return (
            <button
              key={item.id}
              id={tabId}
              type="button"
              role="tab"
              className={[
                'ntq-tabs__tab',
                selected ? 'is-active' : '',
                item.disabled ? 'is-disabled' : '',
              ].filter(Boolean).join(' ')}
              aria-selected={selected}
              aria-controls={panelId}
              tabIndex={selected ? 0 : -1}
              disabled={Boolean(item.disabled)}
              onClick={() => {
                if (!item.disabled) select(item.id);
              }}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      {activeItem ? (
        <div
          id={`${baseId}-panel-${activeItem.id}`}
          role="tabpanel"
          className="ntq-tabs__panel"
          aria-labelledby={`${baseId}-tab-${activeItem.id}`}
        >
          {activeItem.content}
        </div>
      ) : null}
    </div>
  );
}

export default Tabs;
