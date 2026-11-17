import React from 'react';
import './style.scss';

/**
 * 只读键值行列表（详情弹层 / HUD 摘要）。
 *
 * @example
 * <DefinitionList
 *   items={[
 *     { label: '标的', value: '贵州茅台' },
 *     { label: '股数', value: '100 股' },
 *   ]}
 * />
 */
function DefinitionList({
  items = [],
  className = '',
}) {
  const rows = Array.isArray(items) ? items.filter((row) => row && row.label != null) : [];
  if (!rows.length) return null;

  const rootClass = ['ntq-definition-list', className].filter(Boolean).join(' ');

  return (
    <div className={rootClass}>
      {rows.map((row, index) => {
        const key = row.key != null ? row.key : `${row.label}-${index}`;
        return (
          <div key={key} className="ntq-definition-list__row">
            <span className="ntq-definition-list__label">{row.label}</span>
            <span className="ntq-definition-list__value">
              {row.value == null || row.value === false ? '—' : row.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default DefinitionList;
