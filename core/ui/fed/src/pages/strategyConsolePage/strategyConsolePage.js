import React from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  Box,
  Breadcrumbs,
  Link,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

function StrategyConsolePage() {
  const { strategyName } = useParams();

  return (
    <Box sx={{ p: 2 }}>
      <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />} sx={{ mb: 2 }}>
        <Link component={RouterLink} underline="hover" color="inherit" to="/strategy-workbench">
          策略工作台
        </Link>
        <Link component={RouterLink} underline="hover" color="inherit" to="/strategy-workbench">
          策略列表
        </Link>
        {strategyName ? (
          <Typography color="text.primary">调试：{strategyName}</Typography>
        ) : (
          <Typography color="text.primary">策略调试</Typography>
        )}
      </Breadcrumbs>
      <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
        策略调试
        {strategyName ? ` — ${strategyName}` : ''}
      </Typography>
      <Paper variant="outlined" sx={{ p: 3, maxWidth: 720 }}>
        <Stack spacing={1}>
          <Typography color="text.secondary" component="div">
            {strategyName ? (
              <>当前策略为「{strategyName}」。本页为占位，后续可接入单策略扫描、回测、配置编辑等能力。</>
            ) : (
              <>请从「策略列表」中选择策略，或从列表中的策略名 / 进入调试 链入本页（例如路径 /strategy-workbench/example）。</>
            )}
          </Typography>
        </Stack>
      </Paper>
    </Box>
  );
}

export default StrategyConsolePage;
