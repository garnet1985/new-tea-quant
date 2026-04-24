import React from 'react';
import { Box, Container, Typography } from '@mui/material';

function AppFooter() {
  return (
    <Box component="footer" sx={{ mt: 'auto', borderTop: 1, borderColor: 'divider', py: 2 }}>
      <Container maxWidth="lg">
        <Typography variant="body2" color="text.secondary">
          NTQ Prototype - UI mock stage
        </Typography>
      </Container>
    </Box>
  );
}

export default AppFooter;
