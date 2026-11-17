import React from 'react';
import { Separator } from 'ui';
import './style.scss';

function DividerField({ node }) {
  const tight = node?.spacing === 'tight';
  return (
    <Separator
      className={[
        'ntq-editor-divider',
        tight ? 'ntq-editor-divider--tight' : '',
      ].filter(Boolean).join(' ')}
    />
  );
}

export default React.memo(DividerField);
