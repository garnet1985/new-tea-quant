import React from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';

/** 带标题 / 说明的报告内嵌图。无 option 且无 fallback 时不渲染。 */
function ChartPanel({
  title,
  tip,
  option,
  height = 180,
  note,
  fallback,
  sx,
  framed = true,
}) {
  if (!option && fallback == null) return null;
  return (
    <Box
      className="ntq-report-chart-panel"
      sx={{
        ...(framed
          ? { border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }
          : {}),
        minWidth: 0,
        ...sx,
      }}
    >
      {title || tip ? (
        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
          {title ? (
            <Typography variant="caption" color="text.secondary">{title}</Typography>
          ) : null}
          {tip ? <NtqHelpTooltip title={tip} /> : null}
        </Stack>
      ) : null}
      {note ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          {note}
        </Typography>
      ) : null}
      {option ? (
        <ReactECharts
          option={option}
          style={{ height, width: '100%' }}
          notMerge
          lazyUpdate
        />
      ) : fallback}
    </Box>
  );
}

export default ChartPanel;
