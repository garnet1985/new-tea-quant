import React, { useCallback, useEffect, useState } from 'react';
import { Button, Message, Loading } from 'ui';
import { Navigate, Outlet } from 'react-router-dom';
import { fetchLicenseAcceptance } from 'api/licenseApi';

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
    return <Loading variant="page" message="确认使用条款…" className="ntq-loading--min-40vh" />;
  }

  if (loadError) {
    return (
      <div className="ntq-setup-guard-error">
        <Message status="error">{loadError}</Message>
        <Button variant="primary" onClick={retry} className="ntq-setup-guard-error__retry">
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
