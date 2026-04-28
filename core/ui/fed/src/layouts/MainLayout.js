import React from 'react';
import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import AppNavigation from 'components/appNavigation';

function MainLayout() {
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppNavigation />
      <Box component="main" className="ntq-content-inner" sx={{ flex: 1 }}>
        <Outlet />
      </Box>
    </Box>
  );
}

export default MainLayout;
