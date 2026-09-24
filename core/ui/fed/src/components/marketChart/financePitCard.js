import React from 'react';
import { Box, Stack, Typography } from '@mui/material';
import { MARKET_CHART_GRID_LEFT, MARKET_CHART_GRID_RIGHT } from './theme';

const METRIC_DEFS = [
  ['ROE', 'roe'],
  ['EPS', 'eps'],
  ['毛利率', 'gross_profit_margin'],
  ['营收同比', 'or_yoy'],
  ['净利同比', 'netprofit_yoy'],
];

/**
 * 财报 PIT 快照卡：方块常驻；未悬停显示 --，悬停十字线后填数。
 */
export default function FinancePitCard({
  visible = false,
  live = false,
  pointerAsOf = '',
  snapshot = null,
}) {
  if (!visible) return null;
  const snap = snapshot?.snapshot || {};
  return (
    <Box
      sx={{
        ml: `${MARKET_CHART_GRID_LEFT}px`,
        mr: `${MARKET_CHART_GRID_RIGHT}px`,
        px: 1.25,
        py: 1,
        borderRadius: 0,
        bgcolor: 'rgba(255,255,255,0.045)',
        border: '1px solid rgba(255,255,255,0.16)',
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        {live
          ? [
            '财报快照（PIT）',
            pointerAsOf ? `as-of ${pointerAsOf}` : '',
            snapshot?.quarter || '',
            snapshot?.date ? `公告 ${snapshot.date}` : '',
          ].filter(Boolean).join(' · ')
          : '财报快照（悬停 K 线查看 PIT）'}
      </Typography>
      <Stack direction="row" flexWrap="wrap" useFlexGap spacing={1}>
        {METRIC_DEFS.map(([name, key]) => {
          const raw = live ? snap?.[key] : null;
          const n = Number(raw);
          const filled = live && raw != null && Number.isFinite(n);
          const text = filled ? n.toFixed(2) : '--';
          return (
            <Box
              key={name}
              sx={{
                minWidth: 72,
                px: 1,
                py: 0.75,
                borderRadius: 0.75,
                border: '1px solid rgba(255,255,255,0.14)',
                bgcolor: 'rgba(0,0,0,0.22)',
              }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                sx={{ lineHeight: 1.2, mb: 0.35, fontSize: 10 }}
              >
                {name}
              </Typography>
              <Typography
                variant="body2"
                fontWeight={600}
                sx={{
                  fontVariantNumeric: 'tabular-nums',
                  lineHeight: 1.2,
                  color: !filled
                    ? 'text.secondary'
                    : n < 0
                      ? 'error.light'
                      : 'text.primary',
                }}
              >
                {text}
              </Typography>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
