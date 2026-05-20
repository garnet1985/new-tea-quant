import React from 'react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import { Box, Stack, Typography } from '@mui/material';

function MetricCard({ title, value, hint, titleTip }) {
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
      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Typography variant="caption" color="text.secondary">{title}</Typography>
          {titleTip ? <NtqHelpTooltip title={titleTip} /> : null}
        </Stack>
        <Typography
          variant="h6"
          fontWeight={700}
          lineHeight={1.2}
          sx={{ mt: .75 }}
        >
          {value}
        </Typography>
        {hint ? (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
            {hint}
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}

export default MetricCard;
