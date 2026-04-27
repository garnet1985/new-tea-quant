import React from 'react';
import { Box, Stack, Typography } from '@mui/material';

function PriceFactorReport({ title = '价格回测报告（Placeholder）' }) {
  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>
      <Box
        sx={{
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          p: 1.25,
          backgroundColor: 'background.paper',
        }}
      >
        <Stack spacing={0.75}>
          <Typography variant="body2" color="text.secondary">收益率分布与胜率分层</Typography>
          <Typography variant="body2" color="text.secondary">持有周期与回撤摘要</Typography>
          <Typography variant="body2" color="text.secondary">关键参数敏感性视图</Typography>
        </Stack>
      </Box>
    </Stack>
  );
}

export default PriceFactorReport;
