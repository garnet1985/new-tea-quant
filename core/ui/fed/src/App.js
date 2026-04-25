import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import SetupPage from './pages/setupPage';
import ComingSoonPage from './pages/comingSoonPage';
import SetupGuard from './components/setupGuard';
import MainLayout from './layouts/mainLayout';
import StrategyListPage from './pages/strategyListPage';
import StrategyConsolePage from './pages/strategyConsolePage';

const theme = createTheme();

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/setup" element={<SetupPage />} />
          <Route
            element={(
              <SetupGuard>
                <MainLayout />
              </SetupGuard>
            )}
          >
            <Route path="/strategy-workbench/:strategyName" element={<StrategyConsolePage />} />
            <Route path="/strategy-workbench" element={<StrategyListPage />} />
            <Route
              path="/scan"
              element={<ComingSoonPage title="机会扫描" description="全市场/自选池扫描与结果列表将在此提供。" />}
            />
            <Route
              path="/advanced"
              element={(
                <ComingSoonPage
                  title="高级功能"
                  description="数据采集、标签控制台、备份与恢复等入口将集中于此。"
                />
              )}
            />
            <Route
              path="/settings"
              element={<ComingSoonPage title="设置" description="系统、数据路径与运行参数等将在此配置。" />}
            />
          </Route>
          <Route path="*" element={<Navigate to="/strategy-workbench" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
