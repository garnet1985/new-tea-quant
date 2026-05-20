import React from 'react';
import EditorFieldLabel from '../editor/fields/editorFieldLabel';
import {
  Box,
  Stack,
  TextField,
} from '@mui/material';

/**
 * 通用时间段输入：标签 + 可选说明 tooltip + 起止日期。
 * MUI 无内置 DateRange 表单控件，本组件作为薄封装供工作台与其它表单复用。
 */
export default function DateRangeInput({
  label,
  tooltipTitle,
  context = {},
  layout = 'horizontal',
  startLabel = '开始',
  endLabel = '结束',
  startValue = '',
  endValue = '',
  onStartChange,
  onEndChange,
  startError = '',
  endError = '',
}) {
  const isVertical = layout === 'vertical';
  const labelGap = isVertical ? 2 : 1;
  const fieldGap = isVertical ? 1.5 : 1;

  return (
    <Stack spacing={labelGap}>
      {label ? (
        <EditorFieldLabel
          field={{ label, tooltip: tooltipTitle || '' }}
          context={context}
          sx={{ mb: 0 }}
        />
      ) : null}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: isVertical ? '1fr' : { xs: '1fr', md: '1fr 1fr' },
          gap: fieldGap,
        }}
      >
        <TextField
          size="small"
          type="date"
          label={startLabel}
          value={startValue || ''}
          onChange={(e) => onStartChange?.(e.target.value)}
          InputLabelProps={{ shrink: true }}
          error={Boolean(startError)}
          helperText={startError || ''}
          fullWidth
        />
        <TextField
          size="small"
          type="date"
          label={endLabel}
          value={endValue || ''}
          onChange={(e) => onEndChange?.(e.target.value)}
          InputLabelProps={{ shrink: true }}
          error={Boolean(endError)}
          helperText={endError || ''}
          fullWidth
        />
      </Box>
    </Stack>
  );
}
