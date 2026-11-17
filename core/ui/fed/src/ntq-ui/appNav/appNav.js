import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link as RouterLink, useInRouterContext, useLocation } from 'react-router-dom';
import { Popper } from '@mui/material';
import Icon from 'ui/icon/icon';
import './style.scss';

const MENU_CLOSE_DELAY_MS = 160;

function pathActive(pathname, match) {
  if (!match) return false;
  return pathname === match || pathname.startsWith(`${match}/`) || pathname.startsWith(match);
}

function NavButtonLabel({ icon, label, caret = false }) {
  return (
    <>
      {icon ? (
        <Icon name={icon} size="md" className="ntq-nav-btn__icon" />
      ) : null}
      <span className="ntq-nav-btn__label">{label}</span>
      {caret ? (
        <Icon
          name="expandMore"
          size="sm"
          tone="muted"
          className="ntq-nav-btn__caret-icon"
        />
      ) : null}
    </>
  );
}

function AppNavView({
  items = [],
  pathname = '',
  linkComponent: Link = RouterLink,
  className = '',
  ...rest
}) {
  const [openId, setOpenId] = useState(null);
  const closeTimerRef = useRef(null);
  const anchorRefs = useRef({});

  const clearCloseTimer = useCallback(() => {
    if (closeTimerRef.current) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  useEffect(() => () => clearCloseTimer(), [clearCloseTimer]);

  const openMenu = useCallback((id) => {
    clearCloseTimer();
    setOpenId(id);
  }, [clearCloseTimer]);

  const closeMenu = useCallback(() => {
    clearCloseTimer();
    setOpenId(null);
  }, [clearCloseTimer]);

  const scheduleCloseMenu = useCallback(() => {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setOpenId(null);
      closeTimerRef.current = null;
    }, MENU_CLOSE_DELAY_MS);
  }, [clearCloseTimer]);

  const rootClass = ['ntq-nav', className].filter(Boolean).join(' ');

  return (
    <nav className={rootClass} aria-label="主导航" {...rest}>
      {items.map((item, index) => {
        const id = item.id || item.to || item.href || item.label || String(index);
        const children = Array.isArray(item.children) ? item.children : null;

        if (children && children.length > 0) {
          const match = item.match || item.to || '';
          const active = pathActive(pathname, match)
            || children.some((c) => pathActive(pathname, c.match || c.to));
          const open = openId === id;

          return (
            <React.Fragment key={id}>
              <div
                ref={(el) => { anchorRefs.current[id] = el; }}
                className="ntq-nav-dropdown"
                onMouseEnter={() => openMenu(id)}
                onMouseLeave={scheduleCloseMenu}
              >
                <button
                  type="button"
                  className={[
                    'ntq-nav-btn',
                    'ntq-nav-btn--dropdown',
                    active ? 'is-active' : '',
                    open ? 'is-open' : '',
                  ].filter(Boolean).join(' ')}
                  aria-haspopup="true"
                  aria-expanded={open ? 'true' : 'false'}
                  onClick={() => (open ? closeMenu() : openMenu(id))}
                >
                  <NavButtonLabel icon={item.icon} label={item.label} caret />
                </button>
              </div>
              <Popper
                open={open}
                anchorEl={anchorRefs.current[id]}
                placement="bottom-start"
                className="ntq-nav-dropdown-popper"
                modifiers={[
                  { name: 'offset', options: { offset: [0, 0] } },
                  { name: 'preventOverflow', options: { padding: 8 } },
                ]}
              >
                <div
                  className="ntq-nav-dropdown__panel"
                  onMouseEnter={() => openMenu(id)}
                  onMouseLeave={scheduleCloseMenu}
                >
                  {children.map((child) => {
                    const childMatch = child.match || child.to;
                    const selected = pathActive(pathname, childMatch);
                    return (
                      <Link
                        key={child.to || child.label}
                        to={child.to}
                        className={[
                          'ntq-nav-dropdown__item',
                          selected ? 'is-selected' : '',
                        ].filter(Boolean).join(' ')}
                        onClick={closeMenu}
                      >
                        {child.label}
                      </Link>
                    );
                  })}
                </div>
              </Popper>
            </React.Fragment>
          );
        }

        if (item.href) {
          return (
            <a
              key={id}
              href={item.href}
              target={item.external === false ? undefined : '_blank'}
              rel={item.external === false ? undefined : 'noopener noreferrer'}
              className="ntq-nav-btn"
            >
              <NavButtonLabel icon={item.icon} label={item.label} />
            </a>
          );
        }

        const match = item.match || item.to;
        const active = pathActive(pathname, match);
        return (
          <Link
            key={id}
            to={item.to}
            className={['ntq-nav-btn', active ? 'is-active' : ''].filter(Boolean).join(' ')}
          >
            <NavButtonLabel icon={item.icon} label={item.label} />
          </Link>
        );
      })}
    </nav>
  );
}

/** 仅在已有 Router 且未传 pathname 时读取 location。 */
function AppNavFromRouter(props) {
  const location = useLocation();
  return <AppNavView {...props} pathname={location.pathname || ''} />;
}

/**
 * NTQ 顶栏导航（壳）。
 * items 由应用传入，不内置路由表 / 不拉站点 URL。
 *
 * 图鉴请传 pathname + linkComponent（普通 <a>），不要再套 MemoryRouter。
 *
 * item:
 * - { label, to, icon?, match? } 站内链
 * - { label, href, icon?, external? } 外链
 * - { label, icon?, match?, children: [{ label, to, match? }] } 下拉
 *
 * @example
 * <AppNav items={[…]} pathname="/scan" linkComponent={DemoLink} />
 * <AppNav items={[…]} />
 */
function AppNav({ pathname: pathnameProp, ...rest }) {
  const inRouter = useInRouterContext();
  if (pathnameProp != null) {
    return <AppNavView {...rest} pathname={pathnameProp} />;
  }
  if (inRouter) {
    return <AppNavFromRouter {...rest} />;
  }
  return <AppNavView {...rest} pathname="" />;
}

export default AppNav;
