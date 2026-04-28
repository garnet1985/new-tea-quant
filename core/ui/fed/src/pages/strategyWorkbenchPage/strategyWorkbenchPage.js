import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Breadcrumbs,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  Link,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { fetchStrategyList, getStrategyWorkbenchPath } from '../../api/apis/strategyApi';
import { defaultMetaInfo, defaultSettings } from './strategyWorkbench.mock';
import StrategySettingsContainer from './panels/strategySettingsPanel/containers/strategySettingsContainer';
import { normalizeMeta } from './panels/strategySettingsPanel/editorSchemas/strategyMeta';
import StrategyExecutionPanel from './panels/strategyExecutionPanel/strategyExecutionPanel';
import StrategyReportPanel from './panels/strategyReportPanel/strategyReportPanel';
import {
  PlaceholderSection,
  StrategySettingsPanel,
} from './panels/strategySettingsPanel/strategySettingsPanel';

function StrategyWorkbenchPage() {
  const navigate = useNavigate();
  const { strategyName } = useParams();
  const [selectedConfigVersion, setSelectedConfigVersion] = useState('');
  const [configVersions, setConfigVersions] = useState([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingVersionId, setPendingVersionId] = useState('');
  const [moreVersionsOpen, setMoreVersionsOpen] = useState(false);
  const [versionSearch, setVersionSearch] = useState('');
  const [strategyRows, setStrategyRows] = useState([]);
  const [pendingStrategyName, setPendingStrategyName] = useState('');
  const [switchStrategyConfirmOpen, setSwitchStrategyConfirmOpen] = useState(false);
  const [executionState, setExecutionState] = useState({
    stepStatus: {
      enum: 'idle',
      price: 'idle',
      capital: 'idle',
    },
    result: {
      enum: null,
      price: null,
      capital: null,
    },
    compareVersion: {
      enum: '',
      price: '',
      capital: '',
    },
    runningStep: '',
  });
  const initialSettings = useMemo(
    () => ({
      ...defaultSettings,
      meta: normalizeMeta({ ...defaultMetaInfo, name: strategyName || defaultMetaInfo.name }),
    }),
    [strategyName],
  );

  const deepClone = (value) => JSON.parse(JSON.stringify(value));
  const [savedBaselineSettings, setSavedBaselineSettings] = useState(() => deepClone(initialSettings));
  const [appliedSettings, setAppliedSettings] = useState(() => deepClone(initialSettings));
  const [appliedVersionId, setAppliedVersionId] = useState('file_current');

  useEffect(() => {
    setSavedBaselineSettings(deepClone(initialSettings));
    setAppliedSettings(deepClone(initialSettings));
    setAppliedVersionId('file_current');
  }, [initialSettings]);

  useEffect(() => {
    fetchStrategyList()
      .then((res) => {
        setStrategyRows(res.data || []);
      })
      .catch(() => {
        setStrategyRows([]);
      });
  }, []);

  const formatVersionLabel = (versionId, createdAt) => `${versionId}（${createdAt}）`;
  const versionMap = useMemo(
    () => Object.fromEntries(configVersions.map((version) => [version.id, version])),
    [configVersions],
  );
  const latestFiveVersions = useMemo(() => configVersions.slice(0, 5), [configVersions]);
  const displayedVersions = useMemo(() => {
    const keyword = versionSearch.trim().toLowerCase();
    if (!keyword) return latestFiveVersions;
    return configVersions.filter((version) => (
      version.id.toLowerCase().includes(keyword)
      || version.createdAt.toLowerCase().includes(keyword)
    ));
  }, [configVersions, latestFiveVersions, versionSearch]);

  const requestApplyVersion = (versionId) => {
    if (!versionId) return;
    setPendingVersionId(versionId);
    setConfirmOpen(true);
  };
  const closeVersionsDialog = () => {
    setMoreVersionsOpen(false);
    setVersionSearch('');
  };

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
      <StrategySettingsContainer initialSettings={initialSettings}>
        {({ draftSettings, updateSection, setDraftSettings, coreEditor }) => (
          <>
            {(() => {
              const hasUnsavedChanges = JSON.stringify(draftSettings) !== JSON.stringify(savedBaselineSettings);
              const isAppliedSettings = JSON.stringify(draftSettings) === JSON.stringify(appliedSettings);
              const workspaceVersionLabel = selectedConfigVersion || '未保存';
              const appliedVersionLabel = appliedVersionId || 'file_current';
              const visibleStrategies = strategyRows.filter((row) => row?.name && row.name !== strategyName);

              const requestSwitchStrategy = (nextStrategyName) => {
                if (!nextStrategyName) return;
                if (hasUnsavedChanges) {
                  setPendingStrategyName(nextStrategyName);
                  setSwitchStrategyConfirmOpen(true);
                  return;
                }
                navigate(getStrategyWorkbenchPath(nextStrategyName));
              };

              const createWorkspaceVersion = (settingsValue) => {
                const now = new Date();
                const stamp = now.toISOString().replace('T', ' ').slice(0, 19);
                const versionId = `${strategyName || 'strategy'}_${now.getTime()}`;
                setConfigVersions((prev) => ([
                  {
                    id: versionId,
                    createdAt: stamp,
                    settings: deepClone(settingsValue),
                  },
                  ...prev,
                ]));
                setSelectedConfigVersion(versionId);
                setSavedBaselineSettings(deepClone(settingsValue));
                return versionId;
              };

              const handleApplySettings = () => {
                let targetVersionId = selectedConfigVersion;
                if (!targetVersionId || hasUnsavedChanges) {
                  targetVersionId = createWorkspaceVersion(draftSettings);
                }
                setAppliedSettings(deepClone(draftSettings));
                setAppliedVersionId(targetVersionId);
              };

              return (
                <>
            <Box
              sx={{
                mb: 2,
                display: 'flex',
                flexDirection: 'column',
                gap: 1.5,
              }}
            >
              <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
                策略调试
                {strategyName ? ` — ${strategyName}` : ''}
              </Typography>
              <Typography color="text.secondary">
                策略作用是调参数并观察结果变化。本页先按 mock 数据构建完整 UI 骨架。
              </Typography>

              <Box
                sx={{
                  p: 1.5,
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  backgroundColor: 'background.paper',
                }}
              >
                <Stack spacing={1}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Typography variant="subtitle2" fontWeight={700}>应用工作台版本</Typography>
                    <Tooltip title="当前工作台里的修改不会自动写入策略配置。只有点击应用按钮才会写入真实策略配置。">
                      <HelpOutlineIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    </Tooltip>
                  </Stack>
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: { xs: 'column', md: 'row' },
                      alignItems: { xs: 'stretch', md: 'center' },
                      justifyContent: 'space-between',
                      gap: 1,
                    }}
                  >
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} alignItems={{ xs: 'flex-start', md: 'center' }}>
                      <Typography variant="body2">工作台版本：<strong>{workspaceVersionLabel}</strong></Typography>
                      <Typography variant="body2">已应用版本：<strong>{appliedVersionLabel}</strong></Typography>
                      {isAppliedSettings ? (
                        <Chip size="small" color="success" label="策略版本 = 工作台版本" />
                      ) : (
                        <Chip size="small" color="error" label="策略版本 < 工作台版本" />
                      )}
                    </Stack>
                    <Stack direction="row" justifyContent={{ xs: 'flex-start', md: 'flex-end' }}>
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => setMoreVersionsOpen(true)}
                      >
                        应用当前工作台版本到策略
                      </Button>
                    </Stack>
                  </Box>
                </Stack>
              </Box>
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <StrategySettingsPanel
                  settings={draftSettings}
                  onSettingsChange={setDraftSettings}
                  coreEditor={coreEditor}
                  onGoalChange={(nextGoal) => updateSection('goal', nextGoal)}
                  onSamplingChange={(nextSampling) => updateSection('sampling', nextSampling)}
                  onFeesChange={(nextFees) => updateSection('fees', nextFees)}
                  onEnumeratorChange={(nextEnumerator) => updateSection('enumerator', nextEnumerator)}
                  onPriceSimulatorChange={(nextPriceSimulator) => updateSection('price_simulator', nextPriceSimulator)}
                  onCapitalSimulatorChange={(nextCapitalSimulator) => updateSection('capital_simulator', nextCapitalSimulator)}
                />
                <PlaceholderSection
                  title="其他策略"
                >
                  {visibleStrategies.length > 0 ? (
                    <List dense disablePadding>
                      {visibleStrategies.map((row) => (
                        <ListItemButton key={row.id} onClick={() => requestSwitchStrategy(row.name)}>
                          <ListItemText
                            primary={row.name}
                            secondary={row.description || '点击进入策略调试页'}
                          />
                        </ListItemButton>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      暂无其他策略。
                    </Typography>
                  )}
                </PlaceholderSection>
              </Box>
              </Grid>
              <Grid item xs={12} md={9}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <StrategyExecutionPanel
                    settings={draftSettings}
                    onExecutionStateChange={setExecutionState}
                  />
                  <StrategyReportPanel executionState={executionState} />
                </Box>
              </Grid>
            </Grid>

            <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth>
              <DialogTitle>确认应用历史版本</DialogTitle>
              <DialogContent dividers>
                <Typography variant="body2">
                  确定要将历史版本
                  {' '}
                  <strong>{pendingVersionId}</strong>
                  {' '}
                  应用到策略配置吗？当前工作台未保存修改会被覆盖。
                </Typography>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setConfirmOpen(false)}>取消</Button>
                <Button
                  variant="contained"
                  onClick={() => {
                    const target = versionMap[pendingVersionId];
                    if (target) {
                      setDraftSettings(deepClone(target.settings));
                      setSelectedConfigVersion(target.id);
                      setSavedBaselineSettings(deepClone(target.settings));
                      setAppliedSettings(deepClone(target.settings));
                      setAppliedVersionId(target.id);
                    }
                    setConfirmOpen(false);
                  }}
                >
                  确认应用
                </Button>
              </DialogActions>
            </Dialog>

            <Dialog open={moreVersionsOpen} onClose={closeVersionsDialog} maxWidth="sm" fullWidth>
              <DialogTitle>选择工作台版本（最近 5 个）</DialogTitle>
              <DialogContent dividers>
                <Stack spacing={1}>
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="搜索任意历史版本（版本 ID / 时间）"
                    value={versionSearch}
                    onChange={(event) => setVersionSearch(event.target.value)}
                  />
                  <List sx={{ maxHeight: 340, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    {displayedVersions.length > 0 ? displayedVersions.map((version) => (
                      <ListItemButton
                        key={version.id}
                        selected={version.id === selectedConfigVersion}
                        onClick={() => {
                          closeVersionsDialog();
                          requestApplyVersion(version.id);
                        }}
                      >
                        <ListItemText
                          primary={version.id}
                          secondary={version.createdAt}
                        />
                      </ListItemButton>
                    )) : (
                      <Box sx={{ p: 1.5 }}>
                        <Typography variant="body2" color="text.secondary">
                          {configVersions.length > 0 ? '没有匹配的版本。' : '暂无可应用的工作台版本。'}
                        </Typography>
                      </Box>
                    )}
                  </List>
                </Stack>
              </DialogContent>
              <DialogActions>
                <Button onClick={closeVersionsDialog}>关闭</Button>
              </DialogActions>
            </Dialog>
            <Dialog
              open={switchStrategyConfirmOpen}
              onClose={() => setSwitchStrategyConfirmOpen(false)}
              maxWidth="xs"
              fullWidth
            >
              <DialogTitle>存在未保存修改</DialogTitle>
              <DialogContent dividers>
                <Typography variant="body2">
                  当前参数有未保存修改。确定切换到
                  {' '}
                  <strong>{pendingStrategyName}</strong>
                  {' '}
                  吗？未保存内容将丢失。
                </Typography>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setSwitchStrategyConfirmOpen(false)}>取消</Button>
                <Button
                  variant="contained"
                  onClick={() => {
                    const next = pendingStrategyName;
                    setSwitchStrategyConfirmOpen(false);
                    setPendingStrategyName('');
                    if (next) navigate(getStrategyWorkbenchPath(next));
                  }}
                >
                  确认切换
                </Button>
              </DialogActions>
            </Dialog>
          </>
              );
            })()}
          </>
        )}
      </StrategySettingsContainer>
    </Box>
  );
}

export default StrategyWorkbenchPage;
