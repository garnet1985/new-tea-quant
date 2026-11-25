import React from 'react';
import CountTab from 'ui/metric/countTab';
import './style.scss';

/**
 * 「全部 + 横向滚动归类 chips」过滤条。组合 CountTab；选中态与点击由上层控制。
 *
 * @example
 * <CategoryChipStrip
 *   ariaLabel="按归类筛选"
 *   all={{ label: '全部', count: total, selected: !query, onClick: () => setQuery('') }}
 *   items={groups.map((g) => ({
 *     key: g.queryValue,
 *     label: g.category,
 *     count: g.rows.length,
 *     selected: query === g.queryValue,
 *     onClick: () => toggle(g.queryValue),
 *   }))}
 *   selectedItemRef={selectedChipRef}
 * />
 */
function CategoryChipStrip({
  all,
  items = [],
  selectedItemRef = null,
  ariaLabel = '按归类筛选',
  className = '',
}) {
  if (!all && (!items || items.length === 0)) return null;

  const rootClass = ['ntq-category-chip-strip', className].filter(Boolean).join(' ');

  return (
    <div className={rootClass} role="group" aria-label={ariaLabel}>
      {all ? (
        <CountTab
          wide
          label={all.label}
          count={all.count}
          selected={Boolean(all.selected)}
          disabled={all.disabled}
          title={all.title}
          onClick={all.onClick}
        />
      ) : null}
      {items.length > 0 ? (
        <div className="ntq-category-chip-strip__scroller">
          {items.map((item) => {
            const selected = Boolean(item.selected);
            return (
              <CountTab
                key={item.key}
                label={item.label}
                count={item.count}
                title={item.title || item.label}
                selected={selected}
                disabled={item.disabled}
                ref={selected && selectedItemRef ? selectedItemRef : undefined}
                onClick={item.onClick}
              />
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export default CategoryChipStrip;
