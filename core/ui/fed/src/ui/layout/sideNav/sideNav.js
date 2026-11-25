import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { SIDE_NAV_VARIANTS, pickToken } from 'ui/tokens';
import './style.scss';

/** 扩展：默认 sm（rail 项有小圆角）；none=直角 */
const SIDE_NAV_RADIUS_TOKENS = ['sm', 'none'];

/**
 * 左侧目录壳：竖排可点项 + 选中态。
 * 不管版式栏宽（用 Column sidebar）；不管右栏内容（路由 Outlet 或自管）。
 *
 * @example
 * <SideNav
 *   items={[
 *     { id: 'layout', label: '布局', to: '/dev/ui/layout', meta: 4 },
 *     { id: 'button', label: '按钮', to: '/dev/ui/button', meta: 2 },
 *   ]}
 *   activeId="layout"
 *   sticky
 * />
 */
function SideNav({
  items = [],
  activeId = '',
  variant = 'line',
  radius = 'sm',
  sticky = false,
  linkComponent: Link = RouterLink,
  onItemClick,
  className = '',
  'aria-label': ariaLabel = '侧栏导航',
  ...rest
}) {
  const variantToken = pickToken(variant, SIDE_NAV_VARIANTS, 'line');
  const radiusToken = pickToken(radius, SIDE_NAV_RADIUS_TOKENS, 'sm');
  const rootClass = [
    'ntq-side-nav',
    `ntq-side-nav--${variantToken}`,
    radiusToken === 'none' ? 'ntq-side-nav--radius-none' : '',
    sticky ? 'ntq-side-nav--sticky' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <nav className={rootClass} aria-label={ariaLabel} {...rest}>
      <ul className="ntq-side-nav__list">
        {items.map((item) => {
          if (!item || !item.id) return null;
          const active = item.id === activeId;
          const itemClass = [
            'ntq-side-nav__item',
            active ? 'is-active' : '',
            item.disabled ? 'is-disabled' : '',
          ].filter(Boolean).join(' ');

          const body = (
            <>
              <span className="ntq-side-nav__label">{item.label}</span>
              {item.meta != null && item.meta !== false ? (
                <span className="ntq-side-nav__meta">{item.meta}</span>
              ) : null}
            </>
          );

          const sharedProps = {
            className: itemClass,
            'aria-current': active ? 'page' : undefined,
          };

          let node;
          if (item.disabled) {
            node = (
              <span {...sharedProps} aria-disabled="true">
                {body}
              </span>
            );
          } else if (item.to) {
            node = (
              <Link
                {...sharedProps}
                to={item.to}
                onClick={typeof onItemClick === 'function'
                  ? (e) => onItemClick(item.id, e)
                  : undefined}
              >
                {body}
              </Link>
            );
          } else if (item.href) {
            node = (
              <a
                {...sharedProps}
                href={item.href}
                target={item.external === false ? undefined : '_blank'}
                rel={item.external === false ? undefined : 'noopener noreferrer'}
              >
                {body}
              </a>
            );
          } else {
            node = (
              <button
                {...sharedProps}
                type="button"
                onClick={() => {
                  if (typeof onItemClick === 'function') onItemClick(item.id);
                }}
              >
                {body}
              </button>
            );
          }

          return (
            <li key={item.id} className="ntq-side-nav__li">
              {node}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export default SideNav;
