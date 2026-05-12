import React, { useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { AppBar, Box, Toolbar, Typography, Button, Stack } from '@mui/material';
import { ReactComponent as FallbackLogo } from '../assets/icon/tactic.svg';
import './appNavigation.scss';

const navItems = [
  { label: '策略实验室', path: '/strategy-workbench' },
  { label: '策略选股', path: '/scan' },
  { label: '设置', path: '/settings' },
];

function AppNavigation() {
  const location = useLocation();
  const [logoFailed, setLogoFailed] = useState(false);

  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      className="ntq-app-header"
    >
      <Toolbar disableGutters className="ntq-app-header__toolbar">
        <Box
          className="ntq-content-inner"
          sx={{}}
        >
          <Box className="ntq-app-header__inner">
            <Box
              className="ntq-brand"
              component={RouterLink}
              to={navItems[0].path}
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
              <Typography variant="caption" className="ntq-brand__version">
                v0.3.0
              </Typography>
            </Box>
            </Box>
            <Stack direction="row" spacing={0} flexWrap="wrap" className="ntq-nav">
              {navItems.map((item) => {
                const isActive = location.pathname.startsWith(item.path);
                return (
                  <Button
                    key={item.path}
                    component={RouterLink}
                    to={item.path}
                    variant="text"
                    className={`ntq-nav-btn${isActive ? ' is-active' : ''}`}
                  >
                    {item.label}
                  </Button>
                );
              })}
            </Stack>
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default AppNavigation;