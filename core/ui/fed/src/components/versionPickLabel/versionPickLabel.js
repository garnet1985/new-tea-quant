import React from 'react';
import { versionPickMarks } from './versionPickMarks';
import './versionPickLabel.scss';

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
          title={mark.hint}
        >
          {mark.label}
        </span>
      ))}
    </span>
  );
}
