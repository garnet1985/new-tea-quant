import React from 'react';
import { Box, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import TipLabel from 'views/tipLabel';
import { buildMarketChartOption } from './buildMarketChartOption';

/**
 * 无业务语义市场图壳：传入 MarketChartModel 或已构建的 option。
 */
function MarketChart({
  model,
  option: optionProp,
  title,
  tip,
  note,
  height = 420,
  fallback,
  framed = false,
  sx,
}) {
  const option = optionProp || (model ? buildMarketChartOption(model) : null);
  if ((!option || !Object.keys(option).length) && fallback == null) return null;

  return (
    <Box
      className="ntq-market-chart"
      sx={{
        ...(framed
          ? { border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75 }
          : {}),
        minWidth: 0,
        ...sx,
      }}
    >
      <TipLabel variant="caption" tip={tip} className="ntq-tip-label--below">
        {title}
      </TipLabel>
      {note ? (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          {note}
        </Typography>
      ) : null}
      {option && Object.keys(option).length > 0 ? (
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

export default MarketChart;
