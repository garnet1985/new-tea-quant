import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider, createTheme, alpha } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { zhCN as muiZhCN } from '@mui/material/locale';
import SetupPage from './pages/setupPage';
import ComingSoonPage from './pages/comingSoonPage';
import SetupGuard from 'components/setupGuard';
import MainLayout from './layouts/mainLayout';
import StrategyListPage from './pages/strategyListPage';
import StrategyWorkbenchPage from './pages/strategyWorkbenchPage';
import ScanPage from './pages/scanPage';
import SettingsPage from './pages/settingsPage';

/** iOS 风格 Switch：改总宽时只改 `SWITCH_ROOT_WIDTH_PX`，滑块行程 = 轨宽 − 球径 − 左右 padding */
const SWITCH_ROOT_WIDTH_PX = 36;
const SWITCH_THUMB_PX = 16;
/** 与 `padding: 0 2px` 一致：左 2 + 右 2 */
const SWITCH_PAD_X_TOTAL_PX = 4;
const SWITCH_THUMB_TRAVEL_PX = SWITCH_ROOT_WIDTH_PX - SWITCH_THUMB_PX - SWITCH_PAD_X_TOTAL_PX;

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
  components: {
    /** iOS 式：滑块直径小于轨道高度，圆球完全落在胶囊轨道内（不靠默认「大球突出细条」） */
    MuiSwitch: {
      defaultProps: { disableRipple: true },
      styleOverrides: {
        root: {
          width: SWITCH_ROOT_WIDTH_PX,
          height: 24,
          padding: 0,
          display: 'inline-flex',
          alignItems: 'center',
          verticalAlign: 'middle',
          '&.MuiSwitch-sizeSmall': {
            width: SWITCH_ROOT_WIDTH_PX,
            height: 24,
            padding: 0,
          },
          '& .MuiSwitch-switchBase': {
            padding: '0 2px',
            top: '50%',
            transform: 'translateY(-50%)',
            '&.Mui-checked': {
              transform: `translateY(-50%) translateX(${SWITCH_THUMB_TRAVEL_PX}px)`,
            },
          },
        },
        switchBase: ({ theme }) => ({
          left: 0,
          '&.Mui-checked': {
            '& + .MuiSwitch-track': {
              opacity: 1,
              backgroundColor: alpha(theme.palette.primary.main, 0.42),
              borderColor: alpha(theme.palette.primary.main, 0.55),
            },
            '&.Mui-disabled + .MuiSwitch-track': {
              backgroundColor: alpha(theme.palette.primary.main, 0.22),
              borderColor: 'transparent',
            },
          },
          '&.Mui-disabled': {
            '& .MuiSwitch-thumb': {
              backgroundColor: theme.palette.action.disabled,
            },
          },
        }),
        thumb: ({ theme }) => ({
          width: SWITCH_THUMB_PX,
          height: SWITCH_THUMB_PX,
          boxShadow: 'none',
          backgroundColor:
            theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.92)' : theme.palette.common.white,
        }),
        track: ({ theme }) => ({
          opacity: 1,
          borderRadius: 11,
          height: 22,
          boxSizing: 'border-box',
          backgroundColor:
            theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.14)' : theme.palette.grey[400],
          border: `1px solid ${theme.palette.divider}`,
        }),
      },
    },
  },
}, muiZhCN);

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
              element={<SettingsPage />}
            />
          </Route>
          <Route path="*" element={<Navigate to="/strategy-workbench" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
