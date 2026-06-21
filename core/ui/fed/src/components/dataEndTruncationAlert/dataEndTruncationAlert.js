import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Alert, Typography } from '@mui/material';

/**
 * 当 ``data.json`` 配置了 as-of 截断时，在列表页顶部展示统一说明。
 */
export default function DataEndTruncationAlert({ dataEnd, className = '' }) {
  if (!dataEnd?.is_end_date_truncated || !dataEnd?.truncation_hint) {
    return null;
  }

  return (
    <Alert severity="warning" className={className}>
      {dataEnd.truncation_hint}
      {dataEnd.truncation_settings_path ? (
        <>
          {' '}
          <Typography
            component={RouterLink}
            to={dataEnd.truncation_settings_path}
            sx={{ color: 'inherit', fontWeight: 700, textDecoration: 'underline' }}
          >
            前往设置 → 数据范围
          </Typography>
          {' '}
          修改。
        </>
      ) : null}
    </Alert>
  );
}
