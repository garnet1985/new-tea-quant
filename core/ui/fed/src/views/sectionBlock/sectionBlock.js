import React from 'react';
import TipLabel from 'views/tipLabel';
import './style.scss';

function SectionTitle({ title, tip }) {
  return (
    <TipLabel variant="section" tip={tip}>
      {title}
    </TipLabel>
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
