import React, { useCallback, useRef, useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Button,
  Paper,
  Popper,
  Toolbar,
  Typography,
  Stack,
} from '@mui/material';
import { ReactComponent as FallbackLogo } from './ntqIcon/icons/tactic.svg';
import NtqIcon from './ntqIcon/ntqIcon';
import { useAppVersion } from '../hooks/useAppVersion';
import './appNavigation.scss';

/** 主流程导航（不含高级下拉 / 反馈外链） */
const primaryNavItems = [
  { label: '策略选股', path: '/scan', icon: 'monitoring' },
  { label: '制定策略', path: '/strategy-design', icon: 'tactic' },
];

/** 设置放在主导航末项 */
const settingsNavItem = { label: '设置', path: '/settings', icon: 'settings' };

/** 高级功能子菜单（Tag 等） */
const advancedNavItems = [
  { label: '特征标签', path: '/advanced/tags' },
  { label: '数据源', path: '/advanced/data-sources' },
  { label: '数据契约', path: '/advanced/data-contracts' },
];

/** Logo 点击回到的主入口（与主导航第一项一致） */
const HOME_PATH = '/strategy-design';

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

function AppNavigation() {
  const location = useLocation();
  const [logoFailed, setLogoFailed] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const appVersionLabel = useAppVersion();
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
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      className="ntq-app-header"
      sx={{ overflow: 'visible' }}
    >
      <Toolbar disableGutters className="ntq-app-header__toolbar">
        <Box className="ntq-content-inner">
          <Box className="ntq-app-header__inner">
            <Box
              className="ntq-brand"
              component={RouterLink}
              to={HOME_PATH}
              aria-label="返回 New Tea Quant 首页"
            >
              {logoFailed ? (
                <FallbackLogo className="ntq-brand__logo" />
              ) : (
                <Box
                  component="img"
                  src="/logo.png"
                  alt="New Tea Quant 徽标"
                  onError={() => setLogoFailed(true)}
                  className="ntq-brand__logo"
                />
              )}
              <Box className="ntq-brand__meta">
                <Typography variant="h6" className="ntq-brand__name">
                  New Tea Quant
                </Typography>
                {appVersionLabel ? (
                  <Typography variant="caption" className="ntq-brand__version" component="span">
                    {appVersionLabel}
                  </Typography>
                ) : null}
              </Box>
            </Box>
            <Stack direction="row" spacing={0} flexWrap="wrap" className="ntq-nav">
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
            </Stack>
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default AppNavigation;
