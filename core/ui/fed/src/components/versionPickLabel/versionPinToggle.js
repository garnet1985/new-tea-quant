import React from 'react';
import { Button, IconButton, Tooltip } from '@mui/material';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import { versionPinHint } from './versionPickMarks';
import './versionPinToggle.scss';

function stopRowAction(event) {
  event.preventDefault();
  event.stopPropagation();
}

export default function VersionPinToggle({
  version,
  versions,
  disabled = false,
  onToggle,
  showLabel = false,
}) {
  const pinned = Boolean(version?.pinned);
  const vid = String(version?.id || '').trim();
  const hint = versionPinHint(version, versions);
  const label = pinned ? '已固定' : '固定';
  const ariaLabel = pinned ? `取消固定 ${vid}` : `固定 ${vid}`;

  const handleClick = (event) => {
    stopRowAction(event);
    if (!vid || disabled) return;
    onToggle?.(vid);
  };

  const icon = (
    <NtqIcon
      name={pinned ? 'pinFilled' : 'pin'}
      size={20}
      tone={pinned ? 'warning' : 'muted'}
    />
  );

  const control = showLabel ? (
    <Button
      size="small"
      variant="outlined"
      disabled={disabled || !vid}
      onClick={handleClick}
      onMouseDown={stopRowAction}
      startIcon={icon}
      aria-label={ariaLabel}
      className="ntq-version-pin-toggle ntq-version-pin-toggle--labeled"
    >
      {label}
    </Button>
  ) : (
    <IconButton
      size="small"
      disabled={disabled || !vid}
      onClick={handleClick}
      onMouseDown={stopRowAction}
      aria-label={ariaLabel}
      className="ntq-version-pin-toggle ntq-version-row-action"
    >
      {icon}
    </IconButton>
  );

  return (
    <Tooltip title={hint} placement="top">
      <span className="ntq-version-pin-toggle__hit">{control}</span>
    </Tooltip>
  );
}

VersionPinToggle.displayName = 'VersionPinToggle';
