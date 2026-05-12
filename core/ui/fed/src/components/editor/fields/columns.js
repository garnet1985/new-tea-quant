import React from 'react';
import { Box } from '@mui/material';

function ColumnsNode({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  const children = Array.isArray(node.children) ? node.children : [];
  const columns = Number(node.columns) || 1;
  const spans = Array.isArray(node.spans) ? node.spans : [];

  return (
    <Box
      key={node.name}
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: `repeat(${Math.max(1, columns)}, minmax(0, 1fr))` },
        gap: 1,
      }}
    >
      {children.map((child, index) => (
        <Box
          key={child.name || `${node.name}-${index}`}
          sx={spans[index] ? { gridColumn: { md: `span ${spans[index]}` } } : undefined}
        >
          {renderNode(child, value, onChange, errors, emitChangeMeta, context)}
        </Box>
      ))}
    </Box>
  );
}

export default ColumnsNode;
