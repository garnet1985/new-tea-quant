import React from 'react';
import { Stack } from '@mui/material';
import TipLabel from 'views/tipLabel';

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
    <Stack sx={{ mb: EDITOR_FIELD_LABEL_MB, ...sx }}>
      <TipLabel variant="field" tip={title} shine={shine}>
        {field.label}
      </TipLabel>
    </Stack>
  );
}
