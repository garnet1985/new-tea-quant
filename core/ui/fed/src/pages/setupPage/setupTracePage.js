import React, { useCallback, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box } from '@mui/material';
import { saveTraceSettings } from '../../api/settingsApi';
import TraceConsentAskOverlay from '../../components/traceConsentAskOverlay';

/**
 * 安装流水线之后的最后一步：询问使用统计。允许或暂不分享都会进入欢迎页。
 *
 * 本页始终展示。userspace 里已有旧同意记录时也不跳过，避免安装结束被直接送去欢迎页。
 */
function SetupTracePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const source = String(location.state?.source || 'setup_ui').slice(0, 32) || 'setup_ui';
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const decide = useCallback((enabled) => {
    setError('');
    setSaving(true);
    saveTraceSettings({ enabled: Boolean(enabled), source })
      .then(() => {
        navigate('/welcome', { replace: true, state: { playIntro: true } });
      })
      .catch((err) => {
        setError(err?.message || '保存失败，请重试');
      })
      .finally(() => setSaving(false));
  }, [navigate, source]);

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
