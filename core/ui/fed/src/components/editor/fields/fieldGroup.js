import React from 'react';
import { Box, Stack, Typography } from '@mui/material';

function FieldGroupField({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  const children = Array.isArray(node.children) ? node.children : [];

  return (
    <Box key={node.name}>
      <Stack spacing={1}>
        {node.label ? <Typography variant="body2" color="text.secondary">{node.label}</Typography> : null}
        {children.map((child) => renderNode(child, value, onChange, errors, emitChangeMeta, context))}
      </Stack>
    </Box>
  );
}

export default FieldGroupField;