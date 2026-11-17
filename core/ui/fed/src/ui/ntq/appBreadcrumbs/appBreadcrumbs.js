import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import NtqIcon from 'ui/icon/ntqIcon';
import './style.scss';

/**
 * NTQ 面包屑。
 * items: [{ label, to }] 从根到上一层；current 为当前页（不可点）。
 *
 * @example
 * <AppBreadcrumbs
 *   items={[{ label: '策略', to: '/strategies' }]}
 *   current="详情"
 * />
 */
function AppBreadcrumbs({
  items = [],
  current,
  linkComponent: Link = RouterLink,
  className = '',
  ...rest
}) {
  const safeItems = Array.isArray(items)
    ? items.filter((x) => x && x.label && x.to)
    : [];

  const rootClass = ['ntq-breadcrumbs', className].filter(Boolean).join(' ');

  return (
    <nav className={rootClass} aria-label="面包屑" {...rest}>
      <ol className="ntq-breadcrumbs__list">
        {safeItems.map((it, index) => (
          <li key={`${it.to}_${it.label}`} className="ntq-breadcrumbs__li">
            {index > 0 ? (
              <span className="ntq-breadcrumbs__sep" aria-hidden="true">
                <NtqIcon name="chevronRight" size="sm" tone="muted" />
              </span>
            ) : null}
            <Link to={it.to} className="ntq-breadcrumbs__item">
              {it.label}
            </Link>
          </li>
        ))}
        <li className="ntq-breadcrumbs__li">
          {safeItems.length > 0 ? (
            <span className="ntq-breadcrumbs__sep" aria-hidden="true">
              <NtqIcon name="chevronRight" size="sm" tone="muted" />
            </span>
          ) : null}
          <span className="ntq-breadcrumbs__current" aria-current="page">
            {current}
          </span>
        </li>
      </ol>
    </nav>
  );
}

export default AppBreadcrumbs;
