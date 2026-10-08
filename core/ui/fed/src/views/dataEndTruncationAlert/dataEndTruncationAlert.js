import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Typography } from '@mui/material';
import Message from 'views/message';
import './style.scss';

/**
 * 当 ``data.json`` 配置了 as-of 截断时，在列表页顶部展示统一说明。
 */
export default function DataEndTruncationAlert({ dataEnd, className = '' }) {
  if (!dataEnd?.is_end_date_truncated || !dataEnd?.truncation_hint) {
    return null;
  }

  return (
    <Message severity="warning" className={className}>
      {dataEnd.truncation_hint}
      {dataEnd.truncation_settings_path ? (
        <>
          {' '}
          <Typography
            component={RouterLink}
            to={dataEnd.truncation_settings_path}
            className="ntq-data-end-truncation-alert__link"
          >
            前往设置 → 数据范围
          </Typography>
          {' '}
          修改。
        </>
      ) : null}
    </Message>
  );
}
