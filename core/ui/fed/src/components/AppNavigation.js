import React from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { AppBar, Box, Toolbar, Typography, Button, Stack } from '@mui/material';

const navItems = [
  { label: '策略工作台', path: '/strategy-workbench' },
  { label: '机会扫描', path: '/scan' },
  { label: '高级功能', path: '/advanced' },
  { label: '设置', path: '/settings' },
];

function AppNavigation() {
  const location = useLocation();

  return (
    <AppBar position="static" color="default" elevation={1} sx={{ width: '100%' }}>
      <Toolbar disableGutters sx={{ minHeight: 64, display: 'block', width: '100%' }}>
        <Box
          className="ntq-content-inner"
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            minHeight: 64,
            px: 2,
            boxSizing: 'border-box',
          }}
        >
          <Typography variant="h6" fontWeight={600}>
            NTQ Prototype
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {navItems.map((item) => (
              <Button
                key={item.path}
                component={RouterLink}
                to={item.path}
                variant={location.pathname.startsWith(item.path) ? 'contained' : 'text'}
              >
                {item.label}
              </Button>
            ))}
          </Stack>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default AppNavigation;