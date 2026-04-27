import React, { useMemo, useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  Box,
  Breadcrumbs,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  InputLabel,
  List,
  ListItemButton,
  ListItemText,
  Link,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import { defaultMetaInfo, defaultSettings } from './strategyConsole.mock';
import StrategySettingsContainer from './panels/strategySettingsPanel/containers/strategySettingsContainer';
import { normalizeMeta } from './panels/strategySettingsPanel/editorSchemas/strategyMeta';
import StrategyExecutionPanel from './panels/strategyExecutionPanel/strategyExecutionPanel';
import StrategyReportPanel from './panels/strategyReportPanel/strategyReportPanel';
import {
  PlaceholderSection,
  StrategySettingsPanel,
} from './panels/strategySettingsPanel/strategySettingsPanel';

function StrategyConsolePage() {
  const { strategyName } = useParams();
  const [selectedConfigVersion, setSelectedConfigVersion] = useState('');
  const [configVersions, setConfigVersions] = useState([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingVersionId, setPendingVersionId] = useState('');
  const [moreVersionsOpen, setMoreVersionsOpen] = useState(false);
  const [versionSearch, setVersionSearch] = useState('');
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

  const formatVersionLabel = (versionId, createdAt) => `${versionId}（${createdAt}）`;
  const versionMap = useMemo(
    () => Object.fromEntries(configVersions.map((version) => [version.id, version])),
    [configVersions],
  );
  const filteredVersions = useMemo(() => {
    const keyword = versionSearch.trim().toLowerCase();
    if (!keyword) return configVersions;
    return configVersions.filter((version) => (
      version.id.toLowerCase().includes(keyword)
      || version.createdAt.toLowerCase().includes(keyword)
    ));
  }, [configVersions, versionSearch]);

  const requestApplyVersion = (versionId) => {
    if (!versionId) return;
    setPendingVersionId(versionId);
    setConfirmOpen(true);
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
            <Box
              sx={{
                mb: 2,
                display: 'flex',
                alignItems: { xs: 'stretch', md: 'flex-start' },
                justifyContent: 'space-between',
                gap: 1.5,
                flexDirection: { xs: 'column', md: 'row' },
              }}
            >
              <Box>
                <Typography variant="h5" sx={{ mb: 1, fontWeight: 600 }}>
                  策略调试
                  {strategyName ? ` — ${strategyName}` : ''}
                </Typography>
                <Typography color="text.secondary">
                  策略作用是调参数并观察结果变化。本页先按 mock 数据构建完整 UI 骨架。
                </Typography>
              </Box>
              <Stack
                direction={{ xs: 'column', md: 'row' }}
                spacing={1}
                sx={{ minWidth: { xs: '100%', md: 520 }, alignItems: 'center' }}
              >
                <Button
                  variant="contained"
                  size="small"
                  onClick={() => {
                    const now = new Date();
                    const stamp = now.toISOString().replace('T', ' ').slice(0, 19);
                    const versionId = `${strategyName || 'strategy'}_${now.getTime()}`;
                    setConfigVersions((prev) => ([
                      {
                        id: versionId,
                        createdAt: stamp,
                        settings: deepClone(draftSettings),
                      },
                      ...prev,
                    ]));
                    setSelectedConfigVersion(versionId);
                  }}
                >
                  保存当前配置
                </Button>
                <Typography variant="body2" color="text.secondary" sx={{ px: 0.5 }}>
                  或者
                </Typography>
                <Stack direction="row" spacing={0.5} sx={{ width: { xs: '100%', md: 'auto' }, alignItems: 'center' }}>
                  <FormControl size="small" sx={{ minWidth: { xs: '100%', md: 260 }, flex: 1 }}>
                    <InputLabel id="config-version-select-label">恢复到最近版本</InputLabel>
                    <Select
                      labelId="config-version-select-label"
                      value={selectedConfigVersion}
                      label="恢复到最近版本"
                      onChange={(event) => {
                        const nextId = event.target.value;
                        if (!nextId) return;
                        setSelectedConfigVersion(nextId);
                        requestApplyVersion(nextId);
                      }}
                    >
                      <MenuItem value="">
                        <em>请选择版本</em>
                      </MenuItem>
                      {configVersions.slice(0, 10).map((version) => (
                        <MenuItem key={version.id} value={version.id}>
                          {formatVersionLabel(version.id, version.createdAt)}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setMoreVersionsOpen(true)}
                    sx={{ whiteSpace: 'nowrap' }}
                  >
                    恢复到更多版本
                  </Button>
                </Stack>
              </Stack>
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
                  title="回测历史"
                  text="Placeholder：后续展示本策略历史实验记录与可回放版本。"
                />
                <PlaceholderSection
                  title="其他策略"
                  text="Placeholder：后续可横向查看其它策略并做参数参考。"
                />
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
              <DialogTitle>确认恢复配置</DialogTitle>
              <DialogContent dividers>
                <Typography variant="body2">
                  确定要恢复到版本
                  {' '}
                  <strong>{pendingVersionId}</strong>
                  {' '}
                  吗？当前未保存的参数修改会被覆盖。
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
                    }
                    setConfirmOpen(false);
                  }}
                >
                  确认恢复
                </Button>
              </DialogActions>
            </Dialog>

            <Dialog open={moreVersionsOpen} onClose={() => setMoreVersionsOpen(false)} maxWidth="sm" fullWidth>
              <DialogTitle>更多版本</DialogTitle>
              <DialogContent dividers>
                <Stack spacing={1}>
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="搜索版本 ID 或保存时间"
                    value={versionSearch}
                    onChange={(event) => setVersionSearch(event.target.value)}
                  />
                  <List sx={{ maxHeight: 340, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    {filteredVersions.length > 0 ? filteredVersions.map((version) => (
                      <ListItemButton
                        key={version.id}
                        selected={version.id === selectedConfigVersion}
                        onClick={() => {
                          setMoreVersionsOpen(false);
                          setSelectedConfigVersion(version.id);
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
                        <Typography variant="body2" color="text.secondary">没有匹配的版本。</Typography>
                      </Box>
                    )}
                  </List>
                </Stack>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setMoreVersionsOpen(false)}>关闭</Button>
              </DialogActions>
            </Dialog>
          </>
        )}
      </StrategySettingsContainer>
    </Box>
  );
}

export default StrategyConsolePage;
