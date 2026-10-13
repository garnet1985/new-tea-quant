import React, { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Alert, Button } from '@mui/material';
import { getSetupStatus } from 'api/setupApi';
import PageLoadingState from 'views/pageLoadingState';
import './style.scss';

function SetupGuard({ children }) {
  const [loading, setLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  const retry = useCallback(() => {
    setRetryKey((value) => value + 1);
  }, []);

  useEffect(() => {
    let alive = true;
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
  }, [retryKey]);

  if (loading) {
    return <PageLoadingState message="检查系统就绪状态…" minHeight="40vh" />;
  }

  if (loadError) {
    return (
      <div className="ntq-setup-guard-error">
        <Alert severity="error">{loadError}</Alert>
        <Button variant="contained" onClick={retry} className="ntq-setup-guard-error__retry">
          重试
        </Button>
      </div>
    );
  }

  if (!isReady) {
    return <Navigate to="/setup" replace />;
  }

  return children;
}

export default SetupGuard;
