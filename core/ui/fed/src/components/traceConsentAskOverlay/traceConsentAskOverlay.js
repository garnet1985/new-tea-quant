import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Link,
  Typography,
} from '@mui/material';
import { ReactComponent as FallbackLogo } from '../ntqIcon/icons/tactic.svg';
import './traceConsentAskOverlay.scss';

/**
 * 全屏询问是否同意匿名使用统计。主 UI 与安装完成后的成功页可复用。
 * 无关闭入口：必须点同意或不同意。
 */
function TraceConsentAskOverlay({
  open,
  saving,
  error,
  onAllow,
  onDeny,
  detailPath,
}) {
  const [logoFailed, setLogoFailed] = useState(false);

  if (!open) return null;

  return (
    <Box
      className="trace-consent-ask-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="trace-consent-ask-title"
      aria-describedby="trace-consent-ask-desc"
    >
      <Box className="trace-consent-ask-overlay__scrim" aria-hidden />
      <Box className="trace-consent-ask-overlay__panel">
        <Box className="trace-consent-ask-overlay__brand">
          {logoFailed ? (
            <FallbackLogo className="trace-consent-ask-overlay__logo" aria-hidden />
          ) : (
            <Box
              component="img"
              src="/logo.png"
              alt="New Tea Quant"
              className="trace-consent-ask-overlay__logo"
              onError={() => setLogoFailed(true)}
            />
          )}
        </Box>

        <Box className="trace-consent-ask-overlay__body">
          <Typography
            id="trace-consent-ask-title"
            variant="h4"
            component="h1"
            className="trace-consent-ask-overlay__title"
          >
            帮助改进 New Tea Quant？
          </Typography>
          <Typography
            id="trace-consent-ask-desc"
            variant="body1"
            color="text.secondary"
            component="div"
            className="trace-consent-ask-overlay__copy"
          >
            <p className="trace-consent-ask-overlay__p">
              我们希望收集少量
              <strong>匿名使用数据</strong>
              ，用来了解安装/运行问题与框架性能（例如操作系统、机器规格、耗时、调度参数、功能是否成功）。
            </p>
            <p className="trace-consent-ask-overlay__p">
              <strong>不会</strong>
              收集策略内容、行情、回测/扫描结果、文件路径、IP、主机名或任何可识别你本人的信息。
            </p>
            <p className="trace-consent-ask-overlay__p">
              你可以随时在「设置 → 使用统计」中更改选择。
            </p>
          </Typography>

          <Link
            component={RouterLink}
            to={detailPath}
            target="_blank"
            rel="noopener noreferrer"
            underline="always"
            className="trace-consent-ask-overlay__detail-link"
          >
            查看我们具体会收集哪些数据
          </Link>

          {error ? <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert> : null}
        </Box>

        <Box className="trace-consent-ask-overlay__actions">
          <Button
            className="trace-consent-ask-overlay__deny"
            variant="text"
            disableRipple
            disabled={saving}
            onClick={onDeny}
          >
            暂不分享
          </Button>
          <Button
            className="trace-consent-ask-overlay__allow"
            variant="contained"
            color="primary"
            disabled={saving}
            onClick={onAllow}
          >
            {saving ? '保存中…' : '允许分享'}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}

TraceConsentAskOverlay.propTypes = {
  open: PropTypes.bool,
  saving: PropTypes.bool,
  error: PropTypes.string,
  onAllow: PropTypes.func.isRequired,
  onDeny: PropTypes.func.isRequired,
  detailPath: PropTypes.string,
};

TraceConsentAskOverlay.defaultProps = {
  open: false,
  saving: false,
  error: '',
  detailPath: '/what-we-will-track',
};

export default TraceConsentAskOverlay;
