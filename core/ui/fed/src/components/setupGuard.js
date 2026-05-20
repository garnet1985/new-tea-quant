import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getSetupStatus } from '../api/apis/setupApi';
import PageLoadingState from './pageLoadingState/pageLoadingState';

function SetupGuard({ children }) {
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let alive = true;
    getSetupStatus().then((status) => {
      if (!alive) return;
      setIsReady(Boolean(status.isReady));
      setLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [location.pathname]);

  if (loading) {
    return <PageLoadingState message="检查系统就绪状态…" minHeight="40vh" />;
  }

  if (!isReady) {
    return <Navigate to="/setup" replace />;
  }

  return children;
}

export default SetupGuard;
