import React from 'react';
import { Box, Stack, Typography } from '@mui/material';

function FieldGroupField({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  const children = Array.isArray(node.children) ? node.children : [];
  const getChildKey = (child, index) => child?.name || child?.label || `${node.name || 'fieldGroup'}-${index}`;

  return (
    <Box key={node.name}>
      <Stack spacing={1}>
        {node.label ? <Typography variant="body2" color="text.secondary">{node.label}</Typography> : null}
        {children.map((child, index) => (
          <React.Fragment key={getChildKey(child, index)}>
            {renderNode(child, value, onChange, errors, emitChangeMeta, context)}
          </React.Fragment>
        ))}
      </Stack>
    </Box>
  );
}

export default FieldGroupField;