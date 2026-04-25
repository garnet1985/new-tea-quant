import React from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  Box,
  Breadcrumbs,
  Grid,
  Link,
  Typography,
} from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import { defaultMetaInfo, defaultSettings } from './strategyConsole.mock';
import {
  MetaInfoSection,
  PlaceholderSection,
  StrategySettingsSection,
} from './strategyConsoleSections';

function StrategyConsolePage() {
  const { strategyName } = useParams();
  const meta = { ...defaultMetaInfo, name: strategyName || defaultMetaInfo.name };

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
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        策略作用是调参数并观察结果变化。本页先按 mock 数据构建完整 UI 骨架。
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <MetaInfoSection meta={meta} />
            <StrategySettingsSection settings={defaultSettings} />
            <PlaceholderSection
              title="回测历史"
              text="Placeholder：后续展示本策略历史实验记录与可回放版本。"
            />
            <PlaceholderSection
              title="其他策略"
              text="Placeholder：后续可横向查看其它策略并做参数参考。"
            />
          </Box>
        </Grid>
        <Grid item xs={12} md={8}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <PlaceholderSection
              title="执行面板"
              defaultExpanded
              text="Placeholder：三步骤（枚举、价格回测、资金模拟）执行区，后续接任务状态与触发按钮。"
            />
            <PlaceholderSection
              title="模拟结果"
              defaultExpanded
              text="Placeholder：后续展示分层结果摘要、曲线与实验对比。"
            />
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

export default StrategyConsolePage;
