import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { getSetupStatus } from '../api/apis/setupApi';

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
    return (
      <Box sx={{ py: 10, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>检查系统就绪状态...</Typography>
      </Box>
    );
  }

  if (!isReady) {
    return <Navigate to="/setup" replace />;
  }

  return children;
}

export default SetupGuard;
