import React, { useMemo } from 'react';
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
import { metaSectionModel, normalizeMeta } from './models/metaModel';
import StrategySettingsContainer from './containers/strategySettingsContainer';
import MetaCompactEditor from './components/metaCompactEditor';
import {
  PlaceholderSection,
  StrategySettingsSection,
} from './strategyConsoleSections';

function StrategyConsolePage() {
  const { strategyName } = useParams();
  const initialSettings = useMemo(
    () => ({
      ...defaultSettings,
      meta: normalizeMeta({ ...defaultMetaInfo, name: strategyName || defaultMetaInfo.name }),
    }),
    [strategyName],
  );

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

      <StrategySettingsContainer initialSettings={initialSettings}>
        {({ draftSettings, updateSection, coreEditor }) => (
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <MetaCompactEditor
                  sectionTitle={metaSectionModel.sectionTitle}
                  value={draftSettings?.meta}
                  defaultExpanded={metaSectionModel.defaultExpanded}
                  onChange={(nextMeta) => updateSection(metaSectionModel.sectionKey, nextMeta)}
                />
                <StrategySettingsSection
                  settings={draftSettings}
                  coreEditor={coreEditor}
                  onGoalChange={(nextGoal) => updateSection('goal', nextGoal)}
                />
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
        )}
      </StrategySettingsContainer>
    </Box>
  );
}

export default StrategyConsolePage;
