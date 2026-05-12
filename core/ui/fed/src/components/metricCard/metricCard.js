import React from 'react';
import { Box, Stack, Typography } from '@mui/material';

function MetricCard({ title, value, hint }) {
  return (
    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        p: 1.25,
        backgroundColor: 'background.paper',
      }}
    >
      <Stack spacing={0.25}>
        <Typography variant="caption" color="text.secondary">{title}</Typography>
        <Typography variant="h6" fontWeight={700} lineHeight={1.2}>{value}</Typography>
        {hint ? <Typography variant="caption" color="text.secondary">{hint}</Typography> : null}
      </Stack>
    </Box>
  );
}

export default MetricCard;
