import React from 'react';
import { Divider } from '@mui/material';
import './editorFieldGroup.scss';

function DividerField({ node }) {
  return (
    <Divider
      className="ntq-editor-divider"
      sx={{ my: node?.spacing === 'tight' ? 1 : 2.5 }}
    />
  );
}

export default React.memo(DividerField);
