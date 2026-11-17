import React, { useEffect, useState } from 'react';
import { Button, Icon, Message } from 'ui';
import { useNavigate } from 'react-router-dom';
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
    <div className="license-gate" role="dialog" aria-modal="true" aria-labelledby="license-gate-title">
      <div className="license-gate__scrim" aria-hidden />
      <div className="license-gate__panel">
        <div className="license-gate__brand">
          {logoFailed ? (
            <Icon name="tactic" size="xxl" />
          ) : (
            <img
              src="/logo.png"
              alt="New Tea Quant"
              className="license-gate__logo"
              onError={() => setLogoFailed(true)}
            />
          )}
        </div>
        <h1 id="license-gate-title" className="license-gate__title">
          同意使用条款后才能继续
        </h1>
        <div className="license-gate__copy ntq-muted">
          <p>只有同意使用条款，才能继续安装和使用 New Tea Quant。不同意将退出。</p>
          {disclaimerUrl || licenseUrl ? (
            <p>
              {disclaimerUrl ? (
                <a className="ntq-link" href={disclaimerUrl} target="_blank" rel="noopener noreferrer">
                  使用条款
                </a>
              ) : null}
              {disclaimerUrl && licenseUrl ? ' · ' : null}
              {licenseUrl ? (
                <a className="ntq-link" href={licenseUrl} target="_blank" rel="noopener noreferrer">
                  NTQ 许可证
                </a>
              ) : null}
            </p>
          ) : null}
          <p>全文在仓库根目录的 DISCLAIMER.md 与 LICENSE。条款以后改了，会再问一次。</p>
        </div>
        {error ? <Message status="error">{error}</Message> : null}
        {exiting ? <Message status="info">未同意，正在退出。</Message> : null}
        <div className="license-gate__actions">
          <Button variant="ghost" disabled={busy || loading} onClick={decline}>
            不同意并退出
          </Button>
          <Button variant="primary" disabled={busy || loading} onClick={agree}>
            {busy && !exiting ? '保存中…' : '同意并继续'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default SetupLicensePage;
