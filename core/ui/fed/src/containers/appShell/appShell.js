import React from 'react';
import { Outlet } from 'react-router-dom';
import AppNavigation from 'containers/appNavigation';
import AssistantChatDock from 'containers/assistantChatDock';
import GlobalHelperHost from 'containers/globalHelper';
import JobPipelineDock from 'containers/jobPipelineDock';
import JobPipelineWatch from 'containers/jobPipelineWatch';
import { ToastHost } from 'ui';
import PageBackground from 'views/pageBackground';
import './style.scss';

function AppShell() {
  return (
    <div className="ntq-main-layout">
      <AppNavigation />
      <main className="ntq-main-layout__main">
        <PageBackground />
        <div className="ntq-main-layout__main-content ntq-content-inner">
          <Outlet />
        </div>
      </main>
      {/* 全局挂载：切路由不卸载，对话状态保留；整页刷新靠 dock 本地/本机历史恢复 */}
      <AssistantChatDock />
      <GlobalHelperHost />
      <JobPipelineWatch />
      <JobPipelineDock />
      <ToastHost />
    </div>
  );
}

export default AppShell;
