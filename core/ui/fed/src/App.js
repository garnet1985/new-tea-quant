import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import SetupPage from './pages/setupPage';
import ComingSoonPage from './pages/comingSoonPage';
import SetupGuard from 'components/setupGuard';
import MainLayout from './layouts/mainLayout';
import StrategyListPage from './pages/strategyListPage';
import StrategyWorkbenchPage from './pages/strategyWorkbenchPage';
import ScanPage from './pages/scanPage';

const theme = createTheme({
  palette: {
    mode: 'dark',
    // new-tea site tokens: ink background + cyan/violet accent family
    primary: { main: '#22D3EE' }, // cyan
    secondary: { main: '#A855F7' }, // violet
    background: {
      default: '#060612', // ink
      paper: 'rgba(255, 255, 255, 0.06)', // glass surface
    },
    text: {
      primary: 'rgba(255, 255, 255, 0.86)',
      secondary: 'rgba(255, 255, 255, 0.62)',
    },
    divider: 'rgba(255, 255, 255, 0.12)',
  },
  shape: { borderRadius: 5 },
  typography: {
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif",
    h6: { fontWeight: 700 },
    button: { textTransform: 'none', fontWeight: 650, fontSize: 13, letterSpacing: '0.2px' },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/setup" element={<SetupPage />} />
          <Route
            element={(
              <SetupGuard>
                <MainLayout />
              </SetupGuard>
            )}
          >
            <Route path="/strategy-workbench/:strategyName" element={<StrategyWorkbenchPage />} />
            <Route path="/strategy-workbench" element={<StrategyListPage />} />
            <Route
              path="/scan"
              element={<ScanPage />}
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
