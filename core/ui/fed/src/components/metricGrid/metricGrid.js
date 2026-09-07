import React from 'react';
import { Box } from '@mui/material';

function mdTemplate(columns) {
  if (columns === 4) return 'repeat(4, 1fr)';
  if (columns === 3) return 'repeat(3, 1fr)';
  return '1fr 1fr';
}

/** MetricCard 网格：报告区块与归因共用。 */
function MetricGrid({ columns = 2, denseXs = false, children }) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: denseXs ? '1fr 1fr' : '1fr',
          md: mdTemplate(columns),
        },
        gap: 1,
      }}
    >
      {children}
    </Box>
  );
}

export default MetricGrid;
