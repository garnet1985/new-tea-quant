import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import SetupPage from './pages/SetupPage';
import PlaceholderPage from './pages/PlaceholderPage';
import SetupGuard from './components/SetupGuard';
import MainLayout from './layouts/MainLayout';

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
            <Route
              path="/workbench"
              element={<PlaceholderPage title="策略工作台" description="Setup 完成后，这里将接入 workbench 列表页原型。" />}
            />
            <Route
              path="/scan"
              element={<PlaceholderPage title="机会扫描" description="Setup 完成后，这里将接入 scan 页原型。" />}
            />
            <Route
              path="/advanced"
              element={<PlaceholderPage title="高级功能" description="Setup 完成后，这里将接入 data-acquire / tag-console / backup 原型入口。" />}
            />
            <Route
              path="/settings"
              element={<PlaceholderPage title="设置" description="Setup 完成后，这里将接入 settings 页原型。" />}
            />
          </Route>
          <Route path="*" element={<Navigate to="/workbench" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
