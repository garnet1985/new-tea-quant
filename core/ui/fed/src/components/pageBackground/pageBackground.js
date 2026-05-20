import React, { useMemo } from 'react';
import { pickRandomPageBackgroundUrl } from './pageBackgroundCatalog';
import './pageBackground.scss';

function PageBackground() {
  const bgUrl = useMemo(() => pickRandomPageBackgroundUrl(), []);

  if (!bgUrl) return null;

  return (
    <div
      className="ntq-page-background"
      aria-hidden="true"
      style={{ '--ntq-page-bg-url': `url("${bgUrl}")` }}
    >
      <div className="ntq-page-background__photo" />
      <div className="ntq-page-background__veil" />
    </div>
  );
}

export default PageBackground;
