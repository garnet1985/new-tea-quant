import React from 'react';
import NtqHelpTooltip from '../../ntqHelpTooltip/ntqHelpTooltip';
import { Stack, Typography } from '@mui/material';

/** 标签与下方控件（Select / Input 等）的间距（theme spacing 单位） */
export const EDITOR_FIELD_LABEL_MB = 1;

/** 与 Switch 行标签一致：``body2`` + 可选 ``NtqHelpTooltip`` */
export default function EditorFieldLabel({
  field,
  context = {},
  tooltipTitle,
  sx = {},
}) {
  if (!field?.label) return null;
  const title = tooltipTitle ?? field.tooltip ?? '';
  const shine = field.tooltipShine ?? context?.defaultTooltipShine ?? false;

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: EDITOR_FIELD_LABEL_MB, ...sx }}>
      <Typography variant="body2">{field.label}</Typography>
      {title ? <NtqHelpTooltip title={title} shine={shine} /> : null}
    </Stack>
  );
}
