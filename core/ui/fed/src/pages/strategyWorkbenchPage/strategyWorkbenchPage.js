import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
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
import {
  applyStrategySettingsToUserspace,
  fetchCapitalAllocationModeConfig,
  fetchStrategyList,
  fetchStrategySettings,
  fetchStrategyVersions,
  fetchSamplingStrategyConfig,
  restoreStrategyVersion,
  getStrategyWorkbenchPath,
} from '../../api/apis/strategyApi';
import { defaultMetaInfo, defaultSettings } from './strategyWorkbench.mock';
import StrategySettingsContainer from './panels/strategySettingsPanel/containers/strategySettingsContainer';
import { normalizeMeta } from './panels/strategySettingsPanel/editorSchemas/strategyMeta';
import StrategyExecutionPanel from './panels/strategyExecutionPanel/strategyExecutionPanel';
import StrategyReportPanel from './panels/strategyReportPanel/strategyReportPanel';
import {
  buildExecutionResultFromWorkbenchReport,
  mapWorkbenchStepStatusToExecutionCards,
} from './workbenchExecutionHydration';
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
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [settingsError, setSettingsError] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [settingsOptionError, setSettingsOptionError] = useState('');
  const [allocationModeOptions, setAllocationModeOptions] = useState([]);
  const [samplingStrategyOptions, setSamplingStrategyOptions] = useState([]);
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
    runId: '',
    activeRunId: '',
    lastCompletedWorkbenchVersionId: '',
  });
  /** 与 V2-01/恢复后执行面板子组件同步；``key`` 随策略+版本变 */
  const [workbenchExecutionHydration, setWorkbenchExecutionHydration] = useState(null);
  const buildFallbackSettings = useCallback(() => ({
    ...defaultSettings,
    meta: normalizeMeta({ ...defaultMetaInfo, name: strategyName || defaultMetaInfo.name }),
  }), [strategyName]);
  const [initialSettings, setInitialSettings] = useState(() => buildFallbackSettings());

  const deepClone = (value) => JSON.parse(JSON.stringify(value));
  const mergeShapeOnly = useCallback((baseValue, incomingValue) => {
    if (Array.isArray(incomingValue)) return incomingValue;
    if (incomingValue && typeof incomingValue === 'object') {
      const out = {};
      const baseObj = baseValue && typeof baseValue === 'object' && !Array.isArray(baseValue) ? baseValue : {};
      const keys = new Set([
        ...Object.keys(baseObj || {}),
        ...Object.keys(incomingValue || {}),
      ]);
      keys.forEach((key) => {
        const next = incomingValue[key];
        if (next !== undefined) {
          out[key] = mergeShapeOnly(baseObj[key], next);
          return;
        }
        const base = baseObj[key];
        if (Array.isArray(base)) {
          out[key] = [];
        } else if (base && typeof base === 'object') {
          out[key] = mergeShapeOnly(base, {});
        }
      });
      return out;
    }
    return incomingValue;
  }, []);
  const [savedBaselineSettings, setSavedBaselineSettings] = useState(() => deepClone(initialSettings));
  const [appliedSettings, setAppliedSettings] = useState(() => deepClone(initialSettings));
  const [appliedVersionId, setAppliedVersionId] = useState('userspace');
  const [deployConfirmOpen, setDeployConfirmOpen] = useState(false);
  const [userspaceApplyOk, setUserspaceApplyOk] = useState('');
  /** V2-01 初次加载；单步跑完后由 V2-06 progress 的 ``result_report`` 切片合并写入，避免再打一枪 ``version/latest`` */
  const [workbenchResultReport, setWorkbenchResultReport] = useState(null);
  /** 单步跑完后让「模拟结果」 accordion 内 Tab 切到刚完成的回测步 */
  const reportTabFocusSeqRef = useRef(0);
  const [reportTabFocusRequest, setReportTabFocusRequest] = useState(null);
  const handleRunStepComplete = useCallback((step) => {
    if (step !== 'enum' && step !== 'price' && step !== 'capital') return;
    reportTabFocusSeqRef.current += 1;
    setReportTabFocusRequest({ step, tick: reportTabFocusSeqRef.current });
  }, []);

  const forceRunHandlersRef = useRef({ forceEnum: null });

  const mergeWorkbenchResultReportFromProgress = useCallback((slice) => {
    if (!slice || typeof slice !== 'object' || Object.keys(slice).length === 0) return;
    setWorkbenchResultReport((prev) => ({
      ...(prev && typeof prev === 'object' ? prev : {}),
      ...slice,
    }));
  }, []);

  useEffect(() => {
    setSavedBaselineSettings(deepClone(initialSettings));
    setAppliedSettings(deepClone(initialSettings));
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

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchCapitalAllocationModeConfig(),
      fetchSamplingStrategyConfig(),
    ])
      .then(([allocationConfig, samplingConfig]) => {
        if (cancelled) return;
        setAllocationModeOptions(allocationConfig?.options || []);
        setSamplingStrategyOptions(samplingConfig?.options || []);
        setSettingsOptionError('');
      })
      .catch((err) => {
        if (cancelled) return;
        setSettingsOptionError(err?.message || '读取设置选项失败，已使用默认值');
        setAllocationModeOptions([]);
        setSamplingStrategyOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;
    const fallback = buildFallbackSettings();

    if (!strategyName) {
      setConfigVersions([]);
      setSelectedConfigVersion('');
      setInitialSettings(fallback);
      setWorkbenchResultReport(null);
      setWorkbenchExecutionHydration(null);
      setExecutionState({
        stepStatus: { enum: 'idle', price: 'idle', capital: 'idle' },
        result: { enum: null, price: null, capital: null },
        compareVersion: { enum: '', price: '', capital: '' },
        runningStep: '',
        runId: '',
        activeRunId: '',
        lastCompletedWorkbenchVersionId: '',
      });
      setIsLoadingSettings(false);
      setSettingsError('');
      return () => {
        isCancelled = true;
      };
    }

    setIsLoadingSettings(true);
    setSettingsError('');
    setWorkbenchExecutionHydration(null);
    Promise.all([
      fetchStrategyVersions(strategyName),
      fetchStrategySettings(strategyName),
    ])
      .then(([verRes, res]) => {
        if (isCancelled) return;
        const rows = (verRes?.versions || []).map((version) => ({
          id: version.version_id || `v${version.version || ''}`,
          createdAt: version.created_at || '',
          updatedAt: version.updated_at || '',
          version: Number(version.version || 0),
        }));
        setConfigVersions(rows);

        const serverSettings = res?.settings || {};
        const hasServerSettings = serverSettings && typeof serverSettings === 'object' && Object.keys(serverSettings).length > 0;
        const incomingMeta = (
          serverSettings?.meta && typeof serverSettings.meta === 'object'
            ? serverSettings.meta
            : {
              name: serverSettings?.name,
              description: serverSettings?.description,
              is_enabled: serverSettings?.is_enabled,
            }
        );
        const nextSettings = hasServerSettings
          ? mergeShapeOnly(fallback, {
            ...serverSettings,
            meta: normalizeMeta({
              ...incomingMeta,
              name: strategyName,
            }),
          })
          : fallback;
        setInitialSettings(nextSettings);
        setWorkbenchResultReport(res?.result_report ?? null);
        const wbVerRaw = res?.workbench_version_id;
        const wbVer = typeof wbVerRaw === 'string' ? wbVerRaw.trim() : '';
        const stepCards = mapWorkbenchStepStatusToExecutionCards(res?.step_status);
        const execResult = buildExecutionResultFromWorkbenchReport(res?.result_report);
        setWorkbenchExecutionHydration({
          key: `${strategyName}:${wbVer || 'none'}`,
          stepStatus: stepCards,
          result: execResult,
          lastCompletedWorkbenchVersionId: wbVer,
        });
        setExecutionState({
          stepStatus: stepCards,
          result: execResult,
          compareVersion: { enum: '', price: '', capital: '' },
          runningStep: '',
          runId: '',
          activeRunId: '',
          lastCompletedWorkbenchVersionId: wbVer,
        });
        setAppliedVersionId(wbVer !== '' ? wbVer : 'userspace');
        setSelectedConfigVersion(wbVer);
      })
      .catch((err) => {
        if (isCancelled) return;
        setInitialSettings(fallback);
        setWorkbenchResultReport(null);
        setWorkbenchExecutionHydration(null);
        setExecutionState({
          stepStatus: { enum: 'idle', price: 'idle', capital: 'idle' },
          result: { enum: null, price: null, capital: null },
          compareVersion: { enum: '', price: '', capital: '' },
          runningStep: '',
          runId: '',
          activeRunId: '',
          lastCompletedWorkbenchVersionId: '',
        });
        setConfigVersions([]);
        setSettingsError(err?.message || '读取策略配置失败');
      })
      .finally(() => {
        if (!isCancelled) setIsLoadingSettings(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [buildFallbackSettings, mergeShapeOnly, strategyName]);

  const versionMap = useMemo(
    () => Object.fromEntries(configVersions.map((version) => [version.id, version])),
    [configVersions],
  );
  /** 与 `fetchStrategyVersionHistory` 同源（GET …/versions），避免执行/报告面板各打一遍 */
  const compareVersionOptions = useMemo(() => {
    const ids = configVersions
      .map((v) => v.id)
      .filter((id) => typeof id === 'string' && id.trim() !== '');
    return ids.length > 0 ? ['latest', ...ids] : ['latest'];
  }, [configVersions]);
  const latestFiveVersions = useMemo(() => configVersions.slice(0, 5), [configVersions]);
  const displayedVersions = useMemo(() => {
    const keyword = versionSearch.trim().toLowerCase();
    if (!keyword) return latestFiveVersions;
    return configVersions.filter((version) => (
      version.id.toLowerCase().includes(keyword)
      || version.createdAt.toLowerCase().includes(keyword)
      || version.updatedAt.toLowerCase().includes(keyword)
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
              const workspaceVersionLabel = selectedConfigVersion || '（尚无快照）';
              const reportAnchorVersionId = (
                selectedConfigVersion && String(selectedConfigVersion).trim() !== ''
                  ? String(selectedConfigVersion).trim()
                  : (appliedVersionId !== 'userspace' ? String(appliedVersionId).trim() : '')
              );
              const appliedVersionLabel = appliedVersionId === 'userspace'
                ? '策略目录 settings.py（无 DB 快照）'
                : appliedVersionId;
              const visibleStrategies = strategyRows.filter((row) => row?.name && row.name !== strategyName);
              const disableSettingsActions = isSavingSettings || isLoadingSettings || !strategyName;
              const getDraftSettingsForSubmit = () => (
                coreEditor?.getDraftSettingsForSubmit
                  ? coreEditor.getDraftSettingsForSubmit()
                  : draftSettings
              );

              const requestSwitchStrategy = (nextStrategyName) => {
                if (!nextStrategyName) return;
                if (hasUnsavedChanges) {
                  setPendingStrategyName(nextStrategyName);
                  setSwitchStrategyConfirmOpen(true);
                  return;
                }
                navigate(getStrategyWorkbenchPath(nextStrategyName));
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
                策略作用是调参数并观察结果变化。本页设置区已接入 BFF `SWB-04/05`。
              </Typography>
              {isLoadingSettings ? (
                <Typography variant="body2" color="text.secondary">
                  正在加载策略配置...
                </Typography>
              ) : null}
              {settingsError ? (
                <Typography variant="body2" color="error">
                  读取失败：{settingsError}
                </Typography>
              ) : null}
              {saveError ? (
                <Typography variant="body2" color="error">
                  保存失败：{saveError}
                </Typography>
              ) : null}
              {settingsOptionError ? (
                <Typography variant="body2" color="warning.main">
                  选项加载提示：{settingsOptionError}
                </Typography>
              ) : null}
              {userspaceApplyOk ? (
                <Typography variant="body2" color="success.main">
                  {userspaceApplyOk}
                </Typography>
              ) : null}

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
                    <Typography variant="subtitle2" fontWeight={700}>工作台与策略目录</Typography>
                    <Tooltip title="左侧改动默认保存在 DB 快照（执行任一步会先 PUT 快照）；「应用当前工作台版本到策略」才把当前参数写入 userspace 下的 settings.py。">
                      <HelpOutlineIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    </Tooltip>
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    字段合法性以后端校验结果为准；策略目录文件仅在显式发布时覆盖。
                  </Typography>
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
                      <Typography variant="body2">选中快照：<strong>{workspaceVersionLabel}</strong></Typography>
                      <Typography variant="body2">加载来源：<strong>{appliedVersionLabel}</strong></Typography>
                      {isAppliedSettings ? (
                        <Chip size="small" color="success" label="草稿与基线一致" />
                      ) : (
                        <Chip size="small" color="warning" label="草稿相对基线已变更" />
                      )}
                    </Stack>
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent={{ xs: 'stretch', md: 'flex-end' }}>
                      <Button
                        variant="outlined"
                        size="small"
                        disabled={disableSettingsActions}
                        onClick={() => {
                          setSaveError('');
                          setUserspaceApplyOk('');
                          setMoreVersionsOpen(true);
                        }}
                      >
                        历史快照…
                      </Button>
                      <Button
                        variant="contained"
                        size="small"
                        disabled={disableSettingsActions}
                        onClick={() => {
                          setSaveError('');
                          setUserspaceApplyOk('');
                          setDeployConfirmOpen(true);
                        }}
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
                  allocationModeOptions={allocationModeOptions}
                  samplingStrategyOptions={samplingStrategyOptions}
                  onGoalChange={(nextGoal) => updateSection('goal', nextGoal)}
                  onSamplingChange={(nextSampling) => updateSection('sampling', nextSampling)}
                  onFeesChange={(nextFees) => updateSection('fees', nextFees)}
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
                    strategyName={strategyName}
                    settings={draftSettings}
                    getSettingsForRun={getDraftSettingsForSubmit}
                    onExecutionStateChange={setExecutionState}
                    compareVersionOptions={compareVersionOptions}
                    onProgressResultReport={mergeWorkbenchResultReportFromProgress}
                    onRunStepComplete={handleRunStepComplete}
                    workbenchHydration={workbenchExecutionHydration}
                    onRegisterForceHandlers={(api) => {
                      forceRunHandlersRef.current = api || {};
                    }}
                  />
                  <StrategyReportPanel
                    strategyName={strategyName}
                    executionState={executionState}
                    compareVersionOptions={compareVersionOptions}
                    workbenchResultReport={workbenchResultReport}
                    workbenchVersionId={reportAnchorVersionId}
                    reportTabFocusRequest={reportTabFocusRequest}
                    onForceEnumerate={() => forceRunHandlersRef.current?.forceEnum?.()}
                  />
                </Box>
              </Grid>
            </Grid>

            <Dialog open={deployConfirmOpen} onClose={() => setDeployConfirmOpen(false)} maxWidth="xs" fullWidth>
              <DialogTitle>发布到策略目录</DialogTitle>
              <DialogContent dividers>
                <Typography variant="body2">
                  将把当前工作台参数写入该策略在 userspace 下的 settings.py，覆盖目录中的现有文件。
                  此操作不会改动 DB 中的工作台快照（快照仍通过保存/执行步骤累积）。
                </Typography>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setDeployConfirmOpen(false)}>取消</Button>
                <Button
                  variant="contained"
                  disabled={isSavingSettings}
                  onClick={() => {
                    if (!strategyName) {
                      setDeployConfirmOpen(false);
                      return;
                    }
                    setIsSavingSettings(true);
                    setSaveError('');
                    applyStrategySettingsToUserspace(strategyName, getDraftSettingsForSubmit())
                      .then(() => {
                        setUserspaceApplyOk('已写入 userspace 策略 settings.py。');
                        setDeployConfirmOpen(false);
                      })
                      .catch((err) => {
                        setSaveError(err?.message || '发布到策略目录失败');
                      })
                      .finally(() => {
                        setIsSavingSettings(false);
                      });
                  }}
                >
                  {isSavingSettings ? '发布中...' : '确认发布'}
                </Button>
              </DialogActions>
            </Dialog>

            <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth>
              <DialogTitle>恢复历史快照到工作台</DialogTitle>
              <DialogContent dividers>
                <Typography variant="body2">
                  将把快照
                  {' '}
                  <strong>{pendingVersionId}</strong>
                  {' '}
                  恢复为当前工作台内容（写入 DB 新快照，不修改 userspace 下的 settings.py）。
                  未保存的草稿将被覆盖。
                </Typography>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setConfirmOpen(false)}>取消</Button>
                <Button
                  variant="contained"
                  disabled={isSavingSettings}
                  onClick={() => {
                    const target = versionMap[pendingVersionId];
                    if (!target || !strategyName) {
                      setConfirmOpen(false);
                      return;
                    }
                    setIsSavingSettings(true);
                    setSaveError('');
                    restoreStrategyVersion(strategyName, target.id)
                      .then(async (restoreMeta) => {
                        const res = await fetchStrategySettings(strategyName);
                        const vr = await fetchStrategyVersions(strategyName);
                        const rows = (vr?.versions || []).map((version) => ({
                          id: version.version_id || `v${version.version || ''}`,
                          createdAt: version.created_at || '',
                          updatedAt: version.updated_at || '',
                          version: Number(version.version || 0),
                        }));
                        setConfigVersions(rows);
                        setWorkbenchResultReport(res?.result_report ?? null);
                        const wbVerRestore = typeof res?.workbench_version_id === 'string'
                          ? res.workbench_version_id.trim()
                          : '';
                        const stepCardsRestore = mapWorkbenchStepStatusToExecutionCards(res?.step_status);
                        const execResultRestore = buildExecutionResultFromWorkbenchReport(res?.result_report);
                        setWorkbenchExecutionHydration({
                          key: `${strategyName}:${wbVerRestore || String(restoreMeta?.version_id || 'restore')}`,
                          stepStatus: stepCardsRestore,
                          result: execResultRestore,
                          lastCompletedWorkbenchVersionId: wbVerRestore,
                        });
                        setExecutionState({
                          stepStatus: stepCardsRestore,
                          result: execResultRestore,
                          compareVersion: { enum: '', price: '', capital: '' },
                          runningStep: '',
                          runId: '',
                          activeRunId: '',
                          lastCompletedWorkbenchVersionId: wbVerRestore,
                        });
                        const fallback = buildFallbackSettings();
                        const serverSettings = res?.settings || {};
                        const incomingMeta = (
                          serverSettings?.meta && typeof serverSettings.meta === 'object'
                            ? serverSettings.meta
                            : {
                              name: serverSettings?.name,
                              description: serverSettings?.description,
                              is_enabled: serverSettings?.is_enabled,
                            }
                        );
                        const mergedSettings = {
                          ...fallback,
                          ...serverSettings,
                          meta: normalizeMeta({
                            ...fallback.meta,
                            ...incomingMeta,
                            name: strategyName,
                          }),
                        };
                        const wb = wbVerRestore || restoreMeta?.version_id || '';
                        setInitialSettings(mergedSettings);
                        setDraftSettings(deepClone(mergedSettings));
                        setSelectedConfigVersion(wb);
                        setSavedBaselineSettings(deepClone(mergedSettings));
                        setAppliedSettings(deepClone(mergedSettings));
                        setAppliedVersionId(
                          typeof wb === 'string' && wb.trim() !== '' ? wb.trim() : 'userspace',
                        );
                        setConfirmOpen(false);
                      })
                      .catch((err) => {
                        setSaveError(err?.message || '恢复快照失败');
                      })
                      .finally(() => {
                        setIsSavingSettings(false);
                      });
                  }}
                >
                  {isSavingSettings ? '处理中...' : '确认恢复'}
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
                          secondary={version.updatedAt || version.createdAt}
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
