import React from 'react';
import { AppBar, Box, Toolbar } from '@mui/material';
import AppBrand from 'views/appBrand';
import AppNav from 'views/appNav';
import AppVersion from 'containers/appVersion';
import './style.scss';

function AppNavigation() {
  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      className="ntq-app-header"
    >
      <Toolbar disableGutters className="ntq-app-header__toolbar">
        <Box className="ntq-content-inner">
          <Box className="ntq-app-header__inner">
            <AppBrand version={<AppVersion />} />
            <AppNav />
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default AppNavigation;
