import React from 'react';
import { Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import AppNavigation from 'containers/appNavigation';
import AssistantChatDock from 'containers/assistantChatDock';
import GlobalHelperHost from 'containers/globalHelper';
import ToastHost from 'containers/toast';
import PageBackground from 'views/pageBackground';
import './style.scss';

function AppShell() {
  return (
    <Box className="ntq-main-layout">
      <AppNavigation />
      <Box component="main" className="ntq-main-layout__main">
        <PageBackground />
        <Box className="ntq-main-layout__main-content ntq-content-inner">
          <Outlet />
        </Box>
      </Box>
      {/* 全局挂载：切路由不卸载，对话状态保留；整页刷新靠 dock 本地/本机历史恢复 */}
      <AssistantChatDock />
      <GlobalHelperHost />
      <ToastHost />
    </Box>
  );
}

export default AppShell;
