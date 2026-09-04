import React, { useCallback, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Alert, Box, Button, Stack } from '@mui/material';
import { fetchTraceSettings, saveTraceSettings } from '../../api/settingsApi';
import PageLoadingState from '../../components/pageLoadingState/pageLoadingState';
import TraceConsentAskOverlay from '../../components/traceConsentAskOverlay';

/**
 * 安装流水线之后的最后一步：询问使用统计。允许或暂不分享都会进入欢迎页。
 */
function SetupTracePage() {
  const location = useLocation();
  const source = String(location.state?.source || 'setup_ui').slice(0, 32) || 'setup_ui';
  const [loading, setLoading] = useState(true);
  const [needsAsk, setNeedsAsk] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let alive = true;
    fetchTraceSettings()
      .then((result) => {
        if (!alive) return;
        setNeedsAsk(Boolean(result.needs_ask));
        setLoadError('');
      })
      .catch((err) => {
        if (!alive) return;
        setLoadError(err?.message || '无法读取使用统计偏好，请检查网络后重试。');
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const decide = useCallback((enabled) => {
    setError('');
    setSaving(true);
    saveTraceSettings({ enabled: Boolean(enabled), source })
      .then((result) => {
        setNeedsAsk(Boolean(result.needs_ask));
      })
      .catch((err) => {
        setError(err?.message || '保存失败，请重试');
      })
      .finally(() => setSaving(false));
  }, [source]);

  if (loading) {
    return <PageLoadingState message="加载使用统计说明…" minHeight="40vh" />;
  }

  if (loadError) {
    return (
      <Stack spacing={2} sx={{ maxWidth: 480, mx: 'auto', py: 8, px: 2 }}>
        <Alert severity="error">{loadError}</Alert>
        <Button variant="contained" onClick={() => window.location.reload()} sx={{ alignSelf: 'flex-start' }}>
          重试
        </Button>
      </Stack>
    );
  }

  if (!needsAsk) {
    return <Navigate to="/welcome" replace />;
  }

  return (
    <Box sx={{ minHeight: '100vh' }}>
      <TraceConsentAskOverlay
        open
        saving={saving}
        error={error}
        onAllow={() => decide(true)}
        onDeny={() => decide(false)}
      />
    </Box>
  );
}

export default SetupTracePage;
