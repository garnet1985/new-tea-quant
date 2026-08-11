import React, { useCallback, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { fetchTraceSettings, saveTraceSettings } from '../api/apis/settingsApi';
import TraceConsentAskOverlay from './traceConsentAskOverlay';

/**
 * 已进入主 UI 且尚未决定使用统计时，全屏询问（挡住下方）。
 * Overlay 本身可复用；安装向导可直接挂 TraceConsentAskOverlay。
 */
function TraceConsentGuard({ children, source }) {
  const [needsAsk, setNeedsAsk] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    fetchTraceSettings()
      .then((r) => {
        if (!alive) return;
        setNeedsAsk(Boolean(r.needs_ask));
      })
      .catch(() => {
        // 读失败不挡主流程；用户仍可在设置里改
        if (!alive) return;
        setNeedsAsk(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!needsAsk) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [needsAsk]);

  const decide = useCallback((enabled) => {
    setError('');
    setSaving(true);
    saveTraceSettings({ enabled: Boolean(enabled), source })
      .then((r) => {
        setNeedsAsk(Boolean(r.needs_ask));
      })
      .catch((e) => {
        setError(e?.message || '保存失败，请重试');
      })
      .finally(() => setSaving(false));
  }, [source]);

  return (
    <>
      {children}
      <TraceConsentAskOverlay
        open={needsAsk}
        saving={saving}
        error={error}
        onAllow={() => decide(true)}
        onDeny={() => decide(false)}
      />
    </>
  );
}

TraceConsentGuard.propTypes = {
  children: PropTypes.node,
  source: PropTypes.string,
};

TraceConsentGuard.defaultProps = {
  children: null,
  source: 'ask_ui',
};

export default TraceConsentGuard;
