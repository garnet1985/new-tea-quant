import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import Icon from 'views/ntqIcon';
import './style.scss';

// @deprecated 顶栏请用 ntq-ui/appBrand。

const HOME_PATH = '/welcome';

function AppBrand({ to = HOME_PATH, version = null }) {
  const [logoFailed, setLogoFailed] = useState(false);

  return (
    <Box
      className="ntq-brand"
      component={RouterLink}
      to={to}
      aria-label="返回 New Tea Quant 首页"
    >
      {logoFailed ? (
        <Icon name="tactic" size={50} />
      ) : (
        <Box
          component="img"
          src="/logo.png"
          alt="New Tea Quant 徽标"
          onError={() => setLogoFailed(true)}
          className="ntq-brand__logo"
        />
      )}
      <Box className="ntq-brand__meta">
        <Typography variant="h6" className="ntq-brand__name">
          New Tea Quant
        </Typography>
        {version}
      </Box>
    </Box>
  );
}

export default AppBrand;
