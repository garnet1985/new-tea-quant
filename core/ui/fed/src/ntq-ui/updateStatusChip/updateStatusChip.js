import React from 'react';
import { HelpTooltip, Loading, Tag } from 'ui';
import './style.scss';

/**
 * 更新状态标签（数据是否最新 / 是否需重算等）。
 * ``status``: ``up_to_date`` | ``needs_update`` | ``needs_recompute`` | …
 * ``pending``：状态仍在计算 → Loading 小动画 + 文案。
 */
export default function UpdateStatusChip({
  status = '',
  label = '—',
  hint = '',
  pending = false,
}) {
  const key = String(status || '').trim();
  const text = String(label || '—').trim() || '—';

  if (pending) {
    return (
      <Loading
        variant="inlineRow"
        message={text}
        className="ntq-update-status-chip ntq-update-status-chip--pending"
        aria-label={text}
      />
    );
  }

  // 约定：满足 / 完成 → solid；未满足 / 待办 → outline
  let tag;
  if (key === 'up_to_date') {
    tag = <Tag status="success" variant="solid">{text}</Tag>;
  } else if (key === 'needs_update' || key === 'needs_recompute') {
    tag = <Tag status="warning" variant="outline">{text}</Tag>;
  } else {
    tag = <Tag status="neutral" variant="outline">{text}</Tag>;
  }

  if (!hint || key === 'up_to_date') {
    return <span className="ntq-update-status-chip">{tag}</span>;
  }

  return (
    <span className="ntq-update-status-chip ntq-update-status-chip--with-hint">
      {tag}
      <HelpTooltip title={hint} variant="info" />
    </span>
  );
}
