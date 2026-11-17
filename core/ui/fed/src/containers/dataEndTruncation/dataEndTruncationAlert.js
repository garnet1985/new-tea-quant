import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Message from 'ui/message/message';
import './style.scss';

function settingsLinkLabel(path) {
  const p = String(path || '').trim();
  if (p.includes('/membership')) return '前往设置 → 会员';
  if (p.includes('/settings/data') || p.endsWith('/data')) return '前往设置 → 数据范围';
  return '前往设置';
}

/**
 * 演示档 / as-of 截断提示。链接文案跟 ``truncation_settings_path`` 对齐
 *（会员页 vs 数据范围），扫描 / 数据源 / 标签列表共用。
 */
export default function DataEndTruncationAlert({ dataEnd, className = '' }) {
  if (!dataEnd?.is_end_date_truncated || !dataEnd?.truncation_hint) {
    return null;
  }

  const settingsPath = String(dataEnd.truncation_settings_path || '').trim();

  return (
    <Message status="warning" className={className}>
      {dataEnd.truncation_hint}
      {settingsPath ? (
        <>
          {' '}
          <RouterLink
            to={settingsPath}
            className="ntq-link ntq-data-end-truncation-alert__link"
          >
            {settingsLinkLabel(settingsPath)}
          </RouterLink>
          {' '}
          修改。
        </>
      ) : null}
    </Message>
  );
}
