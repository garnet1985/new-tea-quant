import React from 'react';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import {
  Box,
  IconButton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

/**
 * 通用时间段输入：标签 + 可选说明 tooltip + 起止日期。
 * MUI 无内置 DateRange 表单控件，本组件作为薄封装供工作台与其它表单复用。
 */
export default function DateRangeInput({
  label,
  tooltipTitle,
  startLabel = '开始',
  endLabel = '结束',
  startValue = '',
  endValue = '',
  onStartChange,
  onEndChange,
  startError = '',
  endError = '',
}) {
  return (
    <Stack spacing={1}>
      {(label || tooltipTitle) ? (
        <Stack direction="row" alignItems="center" spacing={0.25}>
          {label ? (
            <Typography component="span" variant="subtitle2" fontWeight={600}>
              {label}
            </Typography>
          ) : null}
          {tooltipTitle ? (
            <Tooltip title={tooltipTitle} arrow placement="top">
              <IconButton
                size="small"
                aria-label="时间段说明"
                sx={{ p: 0.25, color: 'text.secondary' }}
              >
                <HelpOutlineIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          ) : null}
        </Stack>
      ) : null}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          gap: 1,
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
