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
  ListSubheader,
  Pagination,
  Select,
  MenuItem,
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
import StrategyReportPanel from './panels/strategyReportPanel/StrategyReportPanel';
import {
  buildExecutionResultFromWorkbenchReport,
  mapWorkbenchStepStatusToExecutionCards,
} from './workbenchExecutionHydration';
import {
  PlaceholderSection,
  StrategySettingsPanel,
} from './panels/strategySettingsPanel/strategySettingsPanel';

/** 左侧草稿 settings 变更后重置右侧执行/报告（加载完成后首次对齐基线，之后任意变更触发 ``onReset``）。core 由容器在 keyup/粘贴时解析写入 ``draftSettings``，签名仅需序列化草稿。 */
function WorkbenchDraftChangeResetBridge({
  draftSettings,
  strategyName,
  isLoadingSettings,
  onReset,
  /** 下一次草稿签名变化来自服务端/容器同步（如恢复快照）时不触发右侧重置 */
  suppressDraftDrivenPanelResetRef,
}) {
  const baselineSigRef = useRef(null);
  const establishedRef = useRef(false);
  const compositeSig = JSON.stringify(draftSettings);

  useEffect(() => {
    if (!strategyName) return;
    if (isLoadingSettings) {
      establishedRef.current = false;
      baselineSigRef.current = null;
      return;
    }
    if (!establishedRef.current) {
      baselineSigRef.current = compositeSig;
      establishedRef.current = true;
      return;
    }
    if (compositeSig !== baselineSigRef.current) {
      baselineSigRef.current = compositeSig;
      if (suppressDraftDrivenPanelResetRef?.current) {
        suppressDraftDrivenPanelResetRef.current = false;
        return;
      }
      onReset();
    }
  }, [
    compositeSig,
    strategyName,
    isLoadingSettings,
    onReset,
    suppressDraftDrivenPanelResetRef,
  ]);

  return null;
}

/** 与执行面板「对比版本」下拉末项一致：打开完整版本列表 */
const RESTORE_MORE_MENU_VALUE = '__restore_more_versions__';
const VERSION_PICKER_PAGE_SIZE = 8;

/** 与 BFF ``workbench_latest_ui_flags.has_persisted_snapshot`` 一致：有效快照 id > 0 */
function versionDetailHasPersistedSnapshot(detail) {
  const vid = String(detail?.version_id ?? '').trim();
  if (!vid) return false;
  const n = Number(String(vid).replace(/^v/i, ''));
  return Number.isFinite(n) && n > 0;
}

/**
 * V2-08 单条快照 → 与 ``fetchStrategySettings``（V2-01）对齐的页面状态，避免恢复后再请求 ``version/latest``。
 * ``has_other_versions``：与后端「≥2 条快照」一致；恢复不写库时用已缓存的 ``GET …/versions`` 列表长度近似。
 */
function workbenchPageStateFromVersionDetail(detail, strategyName, cachedVersionRows) {
  const wbVer = typeof detail?.version_id === 'string' ? detail.version_id.trim() : '';
  const persisted = versionDetailHasPersistedSnapshot(detail);
  const rows = Array.isArray(cachedVersionRows) ? cachedVersionRows : [];
  const hasOtherVersions = persisted && rows.length >= 2;
  return {
    strategy_name: strategyName,
    settings: detail?.settings || {},
    workbench_version_id: wbVer,
    step_status: detail?.step_status,
    result_report: detail?.result_report ?? null,
    has_persisted_snapshot: persisted,
    has_other_versions: hasOtherVersions,
  };
}

function StrategyWorkbenchPage() {
  const navigate = useNavigate();
  const { strategyName } = useParams();
  const [selectedConfigVersion, setSelectedConfigVersion] = useState('');
  const [configVersions, setConfigVersions] = useState([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingVersionId, setPendingVersionId] = useState('');
  const [moreVersionsOpen, setMoreVersionsOpen] = useState(false);
  const [versionSearch, setVersionSearch] = useState('');
  const [versionPickerPage, setVersionPickerPage] = useState(1);
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
  /** V2-01 扩展：是否有 DB 快照、是否还有其它可对比版本（GET …/version/latest） */
  const [hasPersistedSnapshot, setHasPersistedSnapshot] = useState(false);
  const [hasOtherVersions, setHasOtherVersions] = useState(false);
  const syncedWorkbenchVerRef = useRef('');
  /** 恢复快照等场景：草稿由容器跟随 ``initialSettings`` 替换，跳过一轮「草稿变更→清空右侧」 */
  const suppressDraftDrivenPanelResetRef = useRef(false);
  /** 草稿变更时递增，强制执行/报告面板 remount 清空内部 compare / 轮询等状态 */
  const [panelsResetEpoch, setPanelsResetEpoch] = useState(0);

  const resetPanelsAfterDraftChange = useCallback(() => {
    setPanelsResetEpoch((n) => n + 1);
    setWorkbenchResultReport(null);
    setWorkbenchExecutionHydration(null);
    setExecutionState({
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
    setReportTabFocusRequest(null);
  }, []);

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
      setHasPersistedSnapshot(false);
      setHasOtherVersions(false);
      syncedWorkbenchVerRef.current = '';
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
    syncedWorkbenchVerRef.current = '';
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
        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res?.has_other_versions));

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
        syncedWorkbenchVerRef.current = wbVer;
        setAppliedVersionId(wbVer !== '' ? wbVer : 'userspace');
        setSelectedConfigVersion(wbVer);
      })
      .catch((err) => {
        if (isCancelled) return;
        setInitialSettings(fallback);
        setHasPersistedSnapshot(false);
        setHasOtherVersions(false);
        syncedWorkbenchVerRef.current = '';
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

  /** 单步跑完写入新快照后，刷新版本列表与 UI 标志（singleton→第二条快照等） */
  useEffect(() => {
    if (!strategyName || isLoadingSettings) return undefined;
    const v = (executionState.lastCompletedWorkbenchVersionId || '').trim();
    if (!v) return undefined;
    if (v === syncedWorkbenchVerRef.current) return undefined;
    let cancelled = false;
    Promise.all([
      fetchStrategySettings(strategyName),
      fetchStrategyVersions(strategyName),
    ])
      .then(([res, verRes]) => {
        if (cancelled) return;
        const rows = (verRes?.versions || []).map((version) => ({
          id: version.version_id || `v${version.version || ''}`,
          createdAt: version.created_at || '',
          updatedAt: version.updated_at || '',
          version: Number(version.version || 0),
        }));
        setConfigVersions(rows);
        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res?.has_other_versions));
        const wbVer = typeof res?.workbench_version_id === 'string'
          ? res.workbench_version_id.trim()
          : '';
        syncedWorkbenchVerRef.current = wbVer;
        setSelectedConfigVersion(wbVer);
        if (wbVer !== '') {
          setAppliedVersionId(wbVer);
        }
        // 不在此处用 GET latest 覆盖 workbenchResultReport / hydration：易与 V2-06 进度片竞态，导致刚跑完仍显示旧版汇总
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [
    strategyName,
    isLoadingSettings,
    executionState.lastCompletedWorkbenchVersionId,
  ]);

  const versionMap = useMemo(
    () => Object.fromEntries(configVersions.map((version) => [version.id, version])),
    [configVersions],
  );
  const latestFiveVersions = useMemo(() => configVersions.slice(0, 5), [configVersions]);
  /** 与执行器对比下拉一致：最近 5 条，且排除当前工作台快照（恢复自身无意义） */
  const restoreDropdownVersions = useMemo(() => {
    const cur = String(selectedConfigVersion || '').trim();
    return latestFiveVersions.filter((v) => !cur || v.id !== cur);
  }, [latestFiveVersions, selectedConfigVersion]);

  const versionPickerFiltered = useMemo(() => {
    const keyword = versionSearch.trim().toLowerCase();
    if (!keyword) return configVersions;
    return configVersions.filter((version) => (
      version.id.toLowerCase().includes(keyword)
      || version.createdAt.toLowerCase().includes(keyword)
      || version.updatedAt.toLowerCase().includes(keyword)
    ));
  }, [configVersions, versionSearch]);

  const versionPickerTotalPages = Math.max(
    1,
    Math.ceil(versionPickerFiltered.length / VERSION_PICKER_PAGE_SIZE) || 1,
  );

  const versionPickerSlice = useMemo(() => {
    const page = Math.min(versionPickerPage, versionPickerTotalPages);
    const start = (page - 1) * VERSION_PICKER_PAGE_SIZE;
    return versionPickerFiltered.slice(start, start + VERSION_PICKER_PAGE_SIZE);
  }, [versionPickerFiltered, versionPickerPage, versionPickerTotalPages]);

  useEffect(() => {
    setVersionPickerPage(1);
  }, [versionSearch]);

  useEffect(() => {
    setVersionPickerPage((p) => Math.min(p, versionPickerTotalPages));
  }, [versionPickerTotalPages]);

  const requestApplyVersion = (versionId) => {
    if (!versionId) return;
    setPendingVersionId(versionId);
    setConfirmOpen(true);
  };

  const openMoreVersionsDialog = () => {
    setSaveError('');
    setUserspaceApplyOk('');
    setVersionPickerPage(1);
    setMoreVersionsOpen(true);
  };

  const handleRestoreMenuChange = (event) => {
    const value = event.target.value;
    const proceed = () => {
      if (value === RESTORE_MORE_MENU_VALUE) {
        openMoreVersionsDialog();
        return;
      }
      if (value) {
        setSaveError('');
        setUserspaceApplyOk('');
        requestApplyVersion(value);
      }
    };
    window.setTimeout(proceed, 0);
  };

  const closeVersionsDialog = () => {
    setMoreVersionsOpen(false);
    setVersionSearch('');
    setVersionPickerPage(1);
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
            <WorkbenchDraftChangeResetBridge
              key={strategyName || ''}
              draftSettings={draftSettings}
              strategyName={strategyName}
              isLoadingSettings={isLoadingSettings}
              onReset={resetPanelsAfterDraftChange}
              suppressDraftDrivenPanelResetRef={suppressDraftDrivenPanelResetRef}
            />
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

              {hasPersistedSnapshot ? (
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
                      {hasOtherVersions ? (
                        <Select
                          size="small"
                          displayEmpty
                          value=""
                          renderValue={() => '恢复到版本…'}
                          onChange={handleRestoreMenuChange}
                          disabled={disableSettingsActions}
                          sx={{ minWidth: 168 }}
                        >
                          <ListSubheader disableSticky sx={{ lineHeight: '32px', py: 0 }}>
                            恢复到版本…
                          </ListSubheader>
                          {restoreDropdownVersions.map((version) => (
                            <MenuItem key={version.id} value={version.id}>{version.id}</MenuItem>
                          ))}
                          <MenuItem value={RESTORE_MORE_MENU_VALUE}>更多版本…</MenuItem>
                        </Select>
                      ) : null}
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
              ) : null}
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
                    key={`exec-${strategyName || ''}-${panelsResetEpoch}`}
                    strategyName={strategyName}
                    settings={draftSettings}
                    getSettingsForRun={getDraftSettingsForSubmit}
                    onExecutionStateChange={setExecutionState}
                    executionCompareRecentVersionIds={latestFiveVersions.map((v) => v.id)}
                    onProgressResultReport={mergeWorkbenchResultReportFromProgress}
                    onRunStepComplete={handleRunStepComplete}
                    workbenchHydration={workbenchExecutionHydration}
                    onRegisterForceHandlers={(api) => {
                      forceRunHandlersRef.current = api || {};
                    }}
                    showVersionCompare={hasOtherVersions}
                  />
                  <StrategyReportPanel
                    key={`report-${strategyName || ''}-${panelsResetEpoch}`}
                    strategyName={strategyName}
                    executionState={executionState}
                    executionCompareRecentVersionIds={latestFiveVersions.map((v) => v.id)}
                    configVersions={configVersions}
                    workbenchResultReport={workbenchResultReport}
                    reportTabFocusRequest={reportTabFocusRequest}
                    onForceEnumerate={() => forceRunHandlersRef.current?.forceEnum?.()}
                    showReportCompare={hasOtherVersions}
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
                      .then((restoreMeta) => {
                        suppressDraftDrivenPanelResetRef.current = true;
                        const detail = restoreMeta.detail;
                        const res = workbenchPageStateFromVersionDetail(
                          detail,
                          strategyName,
                          configVersions,
                        );
                        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
                        setHasOtherVersions(Boolean(res?.has_other_versions));
                        setWorkbenchResultReport(res?.result_report ?? null);
                        const wbVerRestore = typeof res?.workbench_version_id === 'string'
                          ? res.workbench_version_id.trim()
                          : '';
                        syncedWorkbenchVerRef.current = wbVerRestore;
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
              <DialogTitle>选择工作台版本</DialogTitle>
              <DialogContent dividers>
                <Stack spacing={1}>
                  <TextField
                    size="small"
                    fullWidth
                    placeholder="搜索版本 ID、创建或更新时间"
                    value={versionSearch}
                    onChange={(event) => setVersionSearch(event.target.value)}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {configVersions.length > 0
                      ? `共 ${versionPickerFiltered.length} 条${versionPickerFiltered.length !== configVersions.length ? `（已筛选，全部 ${configVersions.length} 条）` : ''}`
                      : '暂无可选版本'}
                  </Typography>
                  <List sx={{ maxHeight: 340, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    {versionPickerSlice.length > 0 ? versionPickerSlice.map((version) => (
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
                  {versionPickerFiltered.length > VERSION_PICKER_PAGE_SIZE ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', pt: 0.5 }}>
                      <Pagination
                        count={versionPickerTotalPages}
                        page={Math.min(versionPickerPage, versionPickerTotalPages)}
                        onChange={(_event, nextPage) => setVersionPickerPage(nextPage)}
                        size="small"
                        color="primary"
                      />
                    </Box>
                  ) : null}
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
