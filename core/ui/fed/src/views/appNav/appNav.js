import React, { useCallback, useRef, useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Box, Button, Paper, Popper } from '@mui/material';
import NtqIcon from 'views/ntqIcon';
import './style.scss';

const primaryNavItems = [
  { label: '制定策略', path: '/strategy-design', icon: 'tactic' },
  { label: '策略选股', path: '/scan', icon: 'monitoring' },
];

const settingsNavItem = { label: '设置', path: '/settings', icon: 'settings' };

const advancedNavItems = [
  { label: '特征标签', path: '/advanced/tags' },
  { label: '数据源', path: '/advanced/data-sources' },
  { label: '数据契约', path: '/advanced/data-contracts' },
];

const ADVANCED_BASE = '/advanced';
const ADVANCED_MENU_CLOSE_DELAY_MS = 160;
const NAV_ICON_SIZE = 22;

function NavButtonLabel({ icon, label, caret = false }) {
  return (
    <>
      {icon ? (
        <NtqIcon
          name={icon}
          size={NAV_ICON_SIZE}
          className="ntq-nav-btn__icon"
        />
      ) : null}
      <span className="ntq-nav-btn__label">{label}</span>
      {caret ? (
        <NtqIcon
          name="expandMore"
          size={16}
          tone="muted"
          className="ntq-nav-btn__caret-icon"
        />
      ) : null}
    </>
  );
}

function AppNav() {
  const location = useLocation();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const closeTimerRef = useRef(null);
  const dropdownAnchorRef = useRef(null);
  const advancedActive = location.pathname.startsWith(ADVANCED_BASE);

  const clearCloseTimer = useCallback(() => {
    if (closeTimerRef.current) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const openAdvancedMenu = useCallback(() => {
    clearCloseTimer();
    setAdvancedOpen(true);
  }, [clearCloseTimer]);

  const closeAdvancedMenu = useCallback(() => {
    clearCloseTimer();
    setAdvancedOpen(false);
  }, [clearCloseTimer]);

  const scheduleCloseAdvancedMenu = useCallback(() => {
    clearCloseTimer();
    closeTimerRef.current = window.setTimeout(() => {
      setAdvancedOpen(false);
      closeTimerRef.current = null;
    }, ADVANCED_MENU_CLOSE_DELAY_MS);
  }, [clearCloseTimer]);

  const toggleAdvancedMenu = useCallback(() => {
    clearCloseTimer();
    setAdvancedOpen((open) => !open);
  }, [clearCloseTimer]);

  return (
    <Box className="ntq-nav">
      {primaryNavItems.map((item) => {
        const isActive = location.pathname.startsWith(item.path);
        return (
          <Button
            key={item.path}
            component={RouterLink}
            to={item.path}
            variant="text"
            className={`ntq-nav-btn${isActive ? ' is-active' : ''}`}
          >
            <NavButtonLabel icon={item.icon} label={item.label} />
          </Button>
        );
      })}

      <Box
        ref={dropdownAnchorRef}
        className="ntq-nav-dropdown"
        onMouseEnter={openAdvancedMenu}
        onMouseLeave={scheduleCloseAdvancedMenu}
      >
        <Button
          variant="text"
          className={`ntq-nav-btn ntq-nav-btn--dropdown${advancedActive ? ' is-active' : ''}${advancedOpen ? ' is-open' : ''}`}
          aria-haspopup="true"
          aria-expanded={advancedOpen ? 'true' : 'false'}
          onClick={toggleAdvancedMenu}
        >
          <NavButtonLabel icon="dataObject" label="高级功能" caret />
        </Button>
      </Box>
      <Popper
        open={advancedOpen}
        anchorEl={dropdownAnchorRef.current}
        placement="bottom-start"
        className="ntq-nav-dropdown-popper"
        modifiers={[
          { name: 'offset', options: { offset: [0, 0] } },
          { name: 'preventOverflow', options: { padding: 8 } },
        ]}
      >
        <Paper
          elevation={0}
          className="ntq-nav-dropdown__panel"
          onMouseEnter={openAdvancedMenu}
          onMouseLeave={scheduleCloseAdvancedMenu}
        >
          {advancedNavItems.map((item) => {
            const selected = location.pathname.startsWith(item.path);
            return (
              <Box
                key={item.path}
                component={RouterLink}
                to={item.path}
                className={`ntq-nav-dropdown__item${selected ? ' is-selected' : ''}`}
                onClick={closeAdvancedMenu}
              >
                {item.label}
              </Box>
            );
          })}
        </Paper>
      </Popper>

      <Button
        component="a"
        href="https://new-tea.cn/zh-hans/contact?from=ntq_app"
        target="_blank"
        rel="noopener noreferrer"
        variant="text"
        className="ntq-nav-btn"
      >
        <NavButtonLabel icon="chat" label="反馈" />
      </Button>

      <Button
        component={RouterLink}
        to={settingsNavItem.path}
        variant="text"
        className={`ntq-nav-btn${location.pathname.startsWith(settingsNavItem.path) ? ' is-active' : ''}`}
      >
        <NavButtonLabel icon={settingsNavItem.icon} label={settingsNavItem.label} />
      </Button>
    </Box>
  );
}

export default AppNav;
