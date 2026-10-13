import React, { useCallback, useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Alert, Button } from '@mui/material';
import { fetchLicenseAcceptance } from 'api/licenseApi';
import PageLoadingState from 'views/pageLoadingState';

function LicenseGuard() {
  const [loading, setLoading] = useState(true);
  const [accepted, setAccepted] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  const retry = useCallback(() => {
    setRetryKey((value) => value + 1);
  }, []);

  useEffect(() => {
    let alive = true;
    setLoadError('');
    fetchLicenseAcceptance()
      .then((status) => {
        if (!alive) return;
        setAccepted(Boolean(status?.accepted));
      })
      .catch((err) => {
        if (!alive) return;
        setLoadError(err?.message || '无法确认使用条款，请检查后重试。');
        setAccepted(false);
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
    return <PageLoadingState message="确认使用条款…" minHeight="40vh" />;
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

  if (!accepted) {
    return <Navigate to="/setup/license" replace />;
  }

  return <Outlet />;
}

export default LicenseGuard;
