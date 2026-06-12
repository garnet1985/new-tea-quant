import React from 'react';
import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import AppNavigation from 'components/appNavigation';
import PageBackground from 'components/pageBackground/pageBackground';
import './mainLayout.scss';

function MainLayout() {
  return (
    <Box
      className="ntq-main-layout"
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      <AppNavigation />
      <Box
        component="main"
        className="ntq-main-layout__main"
        sx={{ flex: 1, position: 'relative', zIndex: 1, isolation: 'isolate' }}
      >
        <PageBackground />
        <Box className="ntq-main-layout__main-content ntq-content-inner">
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}

export default MainLayout;
