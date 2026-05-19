import React from 'react';
import NtqIcon from '../ntqIcon/ntqIcon';
import { Box, Stack, Tooltip, Typography } from '@mui/material';

function SectionTitle({ title, tip }) {
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <Typography variant="subtitle2" fontWeight={700}>{title}</Typography>
      <Tooltip title={tip} placement="top">
        <NtqIcon name="info" size={15} tone="muted" />
      </Tooltip>
    </Stack>
  );
}

function SectionBlock({ title, tip, children }) {
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
        <SectionTitle title={title} tip={tip} />
        {children}
      </Stack>
    </Box>
  );
}

export { SectionTitle, SectionBlock };
