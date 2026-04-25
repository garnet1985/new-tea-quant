import React from 'react';
import { Box, Typography } from '@mui/material';

function AppFooter() {
  return (
    <Box component="footer" sx={{ mt: 'auto', width: '100%', borderTop: 1, borderColor: 'divider', py: 2 }}>
      <Box className="ntq-content-inner" sx={{ px: 2, boxSizing: 'border-box' }}>
        <Typography variant="body2" color="text.secondary">
          NTQ Prototype - UI mock stage
        </Typography>
      </Box>
    </Box>
  );
}

export default AppFooter;
