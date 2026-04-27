import React from 'react';
import { Box, Stack, Typography } from '@mui/material';

function CapitalAllocationReport({ title = '资金模拟报告（Placeholder）' }) {
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
          <Typography variant="body2" color="text.secondary">资金曲线与净值回放</Typography>
          <Typography variant="body2" color="text.secondary">仓位暴露与资金利用率</Typography>
          <Typography variant="body2" color="text.secondary">分阶段收益归因</Typography>
        </Stack>
      </Box>
    </Stack>
  );
}

export default CapitalAllocationReport;
