import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Link,
  Typography,
} from '@mui/material';
import NtqIcon from 'views/ntqIcon';
import { acceptLicense, declineLicense, fetchLicenseAcceptance } from 'api/licenseApi';
import './setupLicensePage.scss';

function SetupLicensePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [error, setError] = useState('');
  const [logoFailed, setLogoFailed] = useState(false);
  const [disclaimerUrl, setDisclaimerUrl] = useState('');
  const [licenseUrl, setLicenseUrl] = useState('');

  useEffect(() => {
    let alive = true;
    fetchLicenseAcceptance()
      .then((status) => {
        if (!alive) return;
        if (status.disclaimerUrl) setDisclaimerUrl(status.disclaimerUrl);
        if (status.licenseUrl) setLicenseUrl(status.licenseUrl);
        if (status.accepted) {
          navigate('/welcome', { replace: true });
        }
      })
      .catch((err) => {
        if (!alive) return;
        setError(err?.message || '暂时打不开条款状态，仍可打开下面的页面阅读。');
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [navigate]);

  const agree = () => {
    setError('');
    setBusy(true);
    acceptLicense()
      .then(() => {
        navigate('/welcome', { replace: true });
      })
      .catch((err) => {
        setError(err?.message || '保存失败，请重试');
        setBusy(false);
      });
  };

  const decline = () => {
    setError('');
    setBusy(true);
    setExiting(true);
    declineLicense().catch(() => {});
  };

  return (
    <Box className="license-gate" role="dialog" aria-modal="true" aria-labelledby="license-gate-title">
      <Box className="license-gate__scrim" aria-hidden />
      <Box className="license-gate__panel">
        <Box className="license-gate__brand">
          {logoFailed ? (
            <NtqIcon name="tactic" size={64} />
          ) : (
            <Box
              component="img"
              src="/logo.png"
              alt="New Tea Quant"
              className="license-gate__logo"
              onError={() => setLogoFailed(true)}
            />
          )}
        </Box>
        <Typography id="license-gate-title" variant="h4" component="h1" className="license-gate__title">
          同意使用条款后才能继续
        </Typography>
        <Typography variant="body1" color="text.secondary" component="div" className="license-gate__copy">
          <p>只有同意使用条款，才能继续安装和使用 New Tea Quant。不同意将退出。</p>
          {disclaimerUrl || licenseUrl ? (
            <p>
              {disclaimerUrl ? (
                <Link href={disclaimerUrl} target="_blank" rel="noopener noreferrer" underline="always">
                  使用条款
                </Link>
              ) : null}
              {disclaimerUrl && licenseUrl ? ' · ' : null}
              {licenseUrl ? (
                <Link href={licenseUrl} target="_blank" rel="noopener noreferrer" underline="always">
                  NTQ 许可证
                </Link>
              ) : null}
            </p>
          ) : null}
          <p>全文在仓库根目录的 DISCLAIMER.md 与 LICENSE。条款以后改了，会再问一次。</p>
        </Typography>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {exiting ? <Alert severity="info">未同意，正在退出。</Alert> : null}
        <Box className="license-gate__actions">
          <Button variant="text" disabled={busy || loading} onClick={decline}>
            不同意并退出
          </Button>
          <Button variant="contained" color="primary" disabled={busy || loading} onClick={agree}>
            {busy && !exiting ? '保存中…' : '同意并继续'}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

export default SetupLicensePage;
