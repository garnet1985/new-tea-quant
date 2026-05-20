import React from 'react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import { Stack, Typography } from '@mui/material';

/** Accordion 标题行：统一字重，可选区块级 tooltip */
export default function SettingsAccordionTitle({ title, tooltip = '', context = {} }) {
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <Typography component="span" fontWeight={600}>
        {title}
      </Typography>
      {tooltip ? (
        <NtqHelpTooltip
          title={tooltip}
          shine={Boolean(context?.defaultTooltipShine)}
        />
      ) : null}
    </Stack>
  );
}
