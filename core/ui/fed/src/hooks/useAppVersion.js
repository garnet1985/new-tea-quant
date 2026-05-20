import { useEffect, useState } from 'react';
import { fetchAppHealth } from '../api/apis/healthApi';

/** 展示用：``0.3.0`` → ``v0.3.0`` */
export function formatAppVersionLabel(version) {
  const v = String(version || '').trim();
  if (!v) return '';
  return v.startsWith('v') ? v : `v${v}`;
}

/**
 * Header 等处的系统版本：优先 ``GET /api/health``，失败时保留空串（不展示占位假版本）。
 */
export function useAppVersion() {
  const [versionLabel, setVersionLabel] = useState('');

  useEffect(() => {
    let alive = true;
    fetchAppHealth()
      .then(({ version }) => {
        if (!alive) return;
        setVersionLabel(formatAppVersionLabel(version));
      })
      .catch(() => {
        if (!alive) return;
        setVersionLabel('');
      });
    return () => {
      alive = false;
    };
  }, []);

  return versionLabel;
}
