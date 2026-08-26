import React, { useCallback, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Alert, Button, Stack } from '@mui/material';
import { getSetupStatus } from '../api/setupApi';
import PageLoadingState from './pageLoadingState/pageLoadingState';

function SetupGuard({ children }) {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  const retry = useCallback(() => {
    setRetryKey((value) => value + 1);
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setLoadError('');
    getSetupStatus()
      .then((status) => {
        if (!alive) return;
        setIsReady(Boolean(status?.isReady));
      })
      .catch((err) => {
        if (!alive) return;
        setLoadError(err?.message || '无法检查系统就绪状态，请检查网络后重试。');
        setIsReady(false);
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [location.pathname, retryKey]);

  if (loading) {
    return <PageLoadingState message="检查系统就绪状态…" minHeight="40vh" />;
  }

  if (loadError) {
    return (
      <Stack spacing={2} sx={{ maxWidth: 480, mx: 'auto', py: 8, px: 2 }}>
        <Alert severity="error">{loadError}</Alert>
        <Button variant="contained" onClick={retry} sx={{ alignSelf: 'flex-start' }}>
          重试
        </Button>
      </Stack>
    );
  }

  if (!isReady) {
    return <Navigate to="/setup" replace />;
  }

  return children;
}

export default SetupGuard;
