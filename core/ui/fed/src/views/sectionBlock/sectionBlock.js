import React from 'react';
import NtqHelpTooltip from 'views/ntqHelpTooltip';
import { Box, Stack, Typography } from '@mui/material';

function SectionTitle({ title, tip }) {
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <Typography variant="subtitle2" fontWeight={700}>{title}</Typography>
      {tip ? <NtqHelpTooltip title={tip} /> : null}
    </Stack>
  );
}

function SectionBlock({ title, tip, action, children }) {
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
      <Stack spacing={1}>
        {(title || tip || action) ? (
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            spacing={1}
          >
            <SectionTitle title={title} tip={tip} />
            {action || null}
          </Stack>
        ) : null}
        {children}
      </Stack>
    </Box>
  );
}

export { SectionTitle, SectionBlock };
