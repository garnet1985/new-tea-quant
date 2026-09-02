import React from 'react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import { versionPickMarks } from './versionPickMarks';
import './versionPickLabel.scss';

function stopRowAction(event) {
  event.preventDefault();
  event.stopPropagation();
}

function VersionMarkHints({ marks }) {
  return (
    <span className="ntq-version-pick-label__hints">
      {marks.map((mark) => (
        <span key={mark.key} className="ntq-version-pick-label__hint">
          <strong>{mark.label}</strong>
          {mark.hint}
        </span>
      ))}
    </span>
  );
}

export default function VersionPickLabel({ version, id }) {
  const vid = String(id || version?.id || '').trim() || '—';
  const marks = versionPickMarks(version);
  return (
    <span className="ntq-version-pick-label">
      <span className="ntq-version-pick-label__id">{vid}</span>
      {marks.map((mark) => (
        <span
          key={mark.key}
          className={`ntq-version-pick-label__mark ntq-version-pick-label__mark--${mark.key}`}
        >
          {mark.label}
        </span>
      ))}
      {marks.length > 0 ? (
        <span
          className="ntq-version-pick-label__help"
          onClick={stopRowAction}
          onMouseDown={stopRowAction}
          onPointerDown={stopRowAction}
          onKeyDown={stopRowAction}
        >
          <NtqHelpTooltip
            title={<VersionMarkHints marks={marks} />}
            variant="help"
            iconSize={18}
            placement="right"
            ariaLabel="版本标记说明"
          />
        </span>
      ) : null}
    </span>
  );
}
