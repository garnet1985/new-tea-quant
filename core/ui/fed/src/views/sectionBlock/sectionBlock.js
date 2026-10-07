import React from 'react';
import { Typography } from '@mui/material';
import NtqHelpTooltip from 'views/ntqHelpTooltip';
import './style.scss';

function SectionTitle({ title, tip }) {
  return (
    <div className="ntq-section-title">
      <Typography variant="subtitle2" className="ntq-section-title__text">{title}</Typography>
      {tip ? <NtqHelpTooltip title={tip} /> : null}
    </div>
  );
}

function SectionBlock({ title, tip, action, children, className = '' }) {
  const rootClass = ['ntq-section-block', className].filter(Boolean).join(' ');
  return (
    <section className={rootClass}>
      <div className="ntq-section-block__body">
        {(title || tip || action) ? (
          <div className="ntq-section-block__head">
            <SectionTitle title={title} tip={tip} />
            {action || null}
          </div>
        ) : null}
        {children}
      </div>
    </section>
  );
}

export { SectionTitle, SectionBlock };
