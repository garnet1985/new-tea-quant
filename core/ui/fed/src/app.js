import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import theme from './styles/theme';
import SetupPage from './pages/setupPage';
import SetupTracePage from './pages/setupPage/setupTracePage';
import SetupGuard from 'containers/setupGuard';
import FeedbackPromptGuard from 'containers/feedbackPrompt';
import AppShell from 'containers/appShell';
import WelcomePage from './pages/welcomePage';
import StrategyListPage from './pages/strategyListPage';
import StrategyDesignPage from './pages/strategyDesignPage';
import ScanPage from './pages/scanPage';
import TagListPage from './pages/tagPage';
import DataContractListPage from './pages/dataContractPage';
import DataSourceListPage from './pages/dataSourcePage';
import SettingsPage from './pages/settingsPage';
import WhatWeWillTrackPage from './pages/whatWeWillTrackPage';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route
            path="/setup"
            element={<SetupPage />}
          />
          <Route path="/setup/trace" element={<SetupTracePage />} />
          <Route path="/what-we-will-track" element={<WhatWeWillTrackPage />} />
          <Route
            element={(
              <SetupGuard>
                <FeedbackPromptGuard>
                  <AppShell />
                </FeedbackPromptGuard>
              </SetupGuard>
            )}
          >
            <Route path="/welcome" element={<WelcomePage />} />
            <Route
              path="/strategy-workbench/*"
              element={<Navigate to="/strategy-design" replace />}
            />
            <Route
              path="/strategy-workbench"
              element={<Navigate to="/strategy-design" replace />}
            />
            <Route path="/strategy-design">
              <Route index element={<StrategyListPage />} />
              <Route path="*" element={<StrategyDesignPage />} />
            </Route>
            <Route
              path="/scan"
              element={<ScanPage />}
            />
            <Route
              path="/decision"
              element={<Navigate to="/strategy-design" replace />}
            />
            <Route
              path="/decision/play"
              element={<Navigate to="/strategy-design" replace />}
            />
            <Route
              path="/advanced/data-sources"
              element={<DataSourceListPage />}
            />
            <Route
              path="/advanced/data-contracts"
              element={<DataContractListPage />}
            />
            <Route
              path="/advanced/tags"
              element={<TagListPage />}
            />
            <Route
              path="/advanced"
              element={<Navigate to="/advanced/tags" replace />}
            />
            <Route
              path="/tags"
              element={<Navigate to="/advanced/tags" replace />}
            />
            <Route path="/settings/*" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/welcome" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
