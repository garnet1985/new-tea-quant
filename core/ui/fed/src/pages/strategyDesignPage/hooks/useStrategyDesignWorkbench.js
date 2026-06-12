import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  applyStrategySettingsToUserspace,
  downloadStrategyPackage,
  fetchMarketProfileOptions,
  fetchStrategySettings,
  fetchStrategyVersionDetail,
  fetchStrategyVersions,
  restoreStrategyVersion,
} from '../../../api/apis/strategyApi';
import {
  extractStrategyDescription,
  extractStrategyDisplayName,
  normalizeMeta,
} from '../../strategyWorkbenchPage/panels/strategySettingsPanel/editorSchemas/strategyMeta';
import {
  buildWorkbenchExecutionHydrationFromSnapshot,
} from '../../strategyWorkbenchPage/workbenchExecutionHydration';
import {
  buildWorkbenchSnapshotFromSettingsResponse,
  emptyWorkbenchSnapshot,
} from '../../strategyWorkbenchPage/workbenchSnapshot';
import { DESIGN_RESTORE_MORE_MENU_VALUE, VERSION_PICKER_PAGE_SIZE } from '../constants/strategyDesignMetaConstants';
import {
  buildWorkbenchSnapshotFromVersionDetail,
  workbenchPageStateFromVersionDetail,
} from '../lib/workbenchPageState';
import { clearDesignActiveRun } from '../lib/strategyDesignActiveRunPersistence';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { useStrategyDesignExecution } from './useStrategyDesignExecution';

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function mergeShapeOnly(baseValue, incomingValue) {
  if (Array.isArray(incomingValue)) return incomingValue;
  if (incomingValue && typeof incomingValue === 'object') {
    const out = {};
    const baseObj = baseValue && typeof baseValue === 'object' && !Array.isArray(baseValue) ? baseValue : {};
    const keys = new Set([...Object.keys(baseObj || {}), ...Object.keys(incomingValue || {})]);
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
}

function buildMergeBaseSettings() {
  return {
    is_enabled: false,
    meta: normalizeMeta({}),
  };
}

function mapConfigVersionRows(verRes) {
  return (verRes?.versions || []).map((version) => ({
    id: version.version_id || `v${version.version || ''}`,
    createdAt: version.created_at || '',
    updatedAt: version.updated_at || '',
    version: Number(version.version || 0),
  }));
}

/**
 * 制定策略 Layout：工作台快照 / 版本 / settings 加载与 Meta 操作。
 */
export function useStrategyDesignWorkbench() {
  const {
    strategyName,
    session,
    patchSession,
    resetSessionForDraftChange,
    setSession,
  } = useStrategyDesignSession();

  const [configVersions, setConfigVersions] = useState([]);
  const [hasPersistedSnapshot, setHasPersistedSnapshot] = useState(false);
  const [hasOtherVersions, setHasOtherVersions] = useState(false);
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [settingsError, setSettingsError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [userspaceApplyOk, setUserspaceApplyOk] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [strategyDisplayName, setStrategyDisplayName] = useState('');
  const [strategyDescription, setStrategyDescription] = useState('');
  const [initialSettings, setInitialSettings] = useState(() => buildMergeBaseSettings());
  const [draftSettings, setDraftSettings] = useState(() => buildMergeBaseSettings());
  const [savedBaselineSettings, setSavedBaselineSettings] = useState(() => buildMergeBaseSettings());
  const [appliedSettings, setAppliedSettings] = useState(() => buildMergeBaseSettings());
  const [selectedConfigVersion, setSelectedConfigVersion] = useState('');
  const [appliedVersionId, setAppliedVersionId] = useState('userspace');
  const [marketProfileOptions, setMarketProfileOptions] = useState([]);

  const [deployConfirmOpen, setDeployConfirmOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingVersionId, setPendingVersionId] = useState('');
  const [moreVersionsOpen, setMoreVersionsOpen] = useState(false);
  const [versionSearch, setVersionSearch] = useState('');
  const [versionPickerPage, setVersionPickerPage] = useState(1);
  const [packageExporting, setPackageExporting] = useState(false);
  const [packageExportError, setPackageExportError] = useState('');

  const lastRunSyncedVersionRef = useRef('');
  const snapshotSyncGenRef = useRef(0);
  const suppressDraftDrivenPanelResetRef = useRef(false);
  const executionStateRef = useRef(session.executionState);
  executionStateRef.current = session.executionState;

  const getExecutionState = useCallback(() => executionStateRef.current, []);

  const onRunStarted = useCallback(() => {
    lastRunSyncedVersionRef.current = '';
    snapshotSyncGenRef.current += 1;
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchMarketProfileOptions()
      .then((rows) => {
        if (!cancelled) setMarketProfileOptions(Array.isArray(rows) ? rows : []);
      })
      .catch(() => {
        if (!cancelled) setMarketProfileOptions([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setSavedBaselineSettings(deepClone(initialSettings));
    setAppliedSettings(deepClone(initialSettings));
    setDraftSettings(deepClone(initialSettings));
  }, [initialSettings]);

  useEffect(() => {
    let isCancelled = false;
    const mergeBase = buildMergeBaseSettings();

    if (!strategyName) {
      setIsLoadingSettings(false);
      return undefined;
    }

    setStrategyDescription('');
    setStrategyDisplayName('');
    setIsLoadingSettings(true);
    setSettingsError('');
    patchSession({ workbenchSnapshot: emptyWorkbenchSnapshot() });

    Promise.all([
      fetchStrategyVersions(strategyName),
      fetchStrategySettings(strategyName),
    ])
      .then(([verRes, res]) => {
        if (isCancelled) return;
        const rows = mapConfigVersionRows(verRes);
        setConfigVersions(rows);
        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res?.has_other_versions));

        const serverSettings = res?.settings || {};
        const hasServerSettings = serverSettings && typeof serverSettings === 'object'
          && Object.keys(serverSettings).length > 0;
        const incomingMeta = serverSettings?.meta && typeof serverSettings.meta === 'object'
          ? serverSettings.meta
          : {};

        if (hasServerSettings) {
          const nextSettings = mergeShapeOnly(mergeBase, {
            ...serverSettings,
            meta: normalizeMeta(incomingMeta, serverSettings),
          });
          setInitialSettings(nextSettings);
          setStrategyDisplayName(extractStrategyDisplayName(nextSettings) || strategyName);
          setStrategyDescription(extractStrategyDescription(nextSettings));
          setSettingsError('');
        } else {
          setInitialSettings(mergeBase);
          setStrategyDescription('');
          setSettingsError('未返回有效策略配置（settings 为空）。');
        }

        const snapshot = buildWorkbenchSnapshotFromSettingsResponse(res);
        const hydration = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
        const wbVer = snapshot.versionId;
        setSelectedConfigVersion(wbVer);
        setAppliedVersionId(wbVer !== '' ? wbVer : 'userspace');
        lastRunSyncedVersionRef.current = hydration.lastCompletedWorkbenchVersionId;

        patchSession({
          workbenchSnapshot: snapshot,
          draftSettings: hasServerSettings ? mergeShapeOnly(mergeBase, {
            ...serverSettings,
            meta: normalizeMeta(incomingMeta, serverSettings),
          }) : mergeBase,
          appliedSettings: hasServerSettings ? mergeShapeOnly(mergeBase, {
            ...serverSettings,
            meta: normalizeMeta(incomingMeta, serverSettings),
          }) : mergeBase,
          executionState: {
            stepStatus: hydration.stepStatus,
            result: hydration.result,
            compareVersion: { enum: '', price: '', capital: '' },
            runningStep: '',
            runId: '',
            activeRunId: '',
            lastCompletedWorkbenchVersionId: hydration.lastCompletedWorkbenchVersionId,
          },
        });
      })
      .catch((err) => {
        if (isCancelled) return;
        setInitialSettings(mergeBase);
        setHasPersistedSnapshot(false);
        setHasOtherVersions(false);
        setConfigVersions([]);
        setSettingsError(err?.message || '读取策略配置失败');
        patchSession({ workbenchSnapshot: emptyWorkbenchSnapshot() });
      })
      .finally(() => {
        if (!isCancelled) setIsLoadingSettings(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [patchSession, strategyName]);

  useEffect(() => {
    if (!strategyName || isLoadingSettings) return undefined;
    const runVer = (session.executionState?.lastCompletedWorkbenchVersionId || '').trim();
    if (!runVer || runVer === lastRunSyncedVersionRef.current) return undefined;

    const syncGen = snapshotSyncGenRef.current;
    let cancelled = false;

    (async () => {
      try {
        const [detail, verRes] = await Promise.all([
          fetchStrategyVersionDetail(strategyName, runVer),
          fetchStrategyVersions(strategyName),
        ]);
        if (cancelled || syncGen !== snapshotSyncGenRef.current) return;
        const rows = mapConfigVersionRows(verRes);
        setConfigVersions(rows);
        const res = workbenchPageStateFromVersionDetail(detail, strategyName, rows);
        const snapshot = buildWorkbenchSnapshotFromVersionDetail(detail);
        const hydration = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
        const wbVer = res.workbench_version_id || runVer;
        setHasPersistedSnapshot(Boolean(res.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res.has_other_versions));
        setSelectedConfigVersion(wbVer);
        setAppliedVersionId(wbVer);
        lastRunSyncedVersionRef.current = wbVer;
        patchSession({
          workbenchSnapshot: snapshot,
          executionState: {
            ...session.executionState,
            stepStatus: hydration.stepStatus,
            result: hydration.result,
            lastCompletedWorkbenchVersionId: wbVer,
          },
        });
      } catch {
        /* 保留上一轮快照 */
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    isLoadingSettings,
    patchSession,
    session.executionState,
    strategyName,
  ]);

  const versionMap = useMemo(
    () => Object.fromEntries(configVersions.map((version) => [version.id, version])),
    [configVersions],
  );

  const latestFiveVersions = useMemo(() => configVersions.slice(0, 5), [configVersions]);

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

  const isAppliedSettings = useMemo(
    () => JSON.stringify(draftSettings) === JSON.stringify(appliedSettings),
    [appliedSettings, draftSettings],
  );

  const currentVersionDisplay = useMemo(() => {
    const workspaceVersionLabel = selectedConfigVersion || '（尚无快照）';
    if (appliedVersionId === 'userspace') return 'settings文件';
    return String(appliedVersionId || '').trim() || workspaceVersionLabel;
  }, [appliedVersionId, selectedConfigVersion]);

  const marketProfileLabel = useMemo(() => {
    const mp = draftSettings?.market_profile
      || draftSettings?.meta?.market_profile
      || initialSettings?.market_profile
      || initialSettings?.meta?.market_profile
      || '';
    const row = marketProfileOptions.find((o) => o.value === mp);
    return row?.label || mp || '—';
  }, [draftSettings, initialSettings, marketProfileOptions]);

  const getDraftSettingsForSubmit = useCallback(
    () => deepClone(draftSettings),
    [draftSettings],
  );

  const {
    runError,
    progressDetail,
    handleRunCurrentStep,
    forceEnumerate,
    executionBusy,
  } = useStrategyDesignExecution({
    strategyName,
    activeStep: session.activeStep,
    getDraftSettingsForSubmit,
    setAppliedSettings,
    isLoadingSettings,
    onRunStarted,
    setSession,
    getExecutionState,
  });

  const disableMetaActions = isSavingSettings || isLoadingSettings || !strategyName || executionBusy;

  const handleDraftDrivenReset = useCallback(() => {
    if (strategyName) clearDesignActiveRun(strategyName);
    setSelectedConfigVersion('');
    setAppliedVersionId('userspace');
    lastRunSyncedVersionRef.current = '';
    resetSessionForDraftChange();
  }, [resetSessionForDraftChange, strategyName]);

  const requestApplyVersion = useCallback((versionId) => {
    if (!versionId) return;
    setPendingVersionId(versionId);
    setConfirmOpen(true);
  }, []);

  const openMoreVersionsDialog = useCallback(() => {
    setSaveError('');
    setUserspaceApplyOk('');
    setVersionPickerPage(1);
    setMoreVersionsOpen(true);
  }, []);

  const closeVersionsDialog = useCallback(() => {
    setMoreVersionsOpen(false);
    setVersionSearch('');
    setVersionPickerPage(1);
  }, []);

  const handleRestoreMenuChange = useCallback((event) => {
    const value = event.target.value;
    window.setTimeout(() => {
      if (value === DESIGN_RESTORE_MORE_MENU_VALUE) {
        openMoreVersionsDialog();
        return;
      }
      if (value) {
        setSaveError('');
        setUserspaceApplyOk('');
        requestApplyVersion(value);
      }
    }, 0);
  }, [openMoreVersionsDialog, requestApplyVersion]);

  const handleExportStrategyPackage = useCallback(async () => {
    if (!strategyName) return;
    setPackageExporting(true);
    setPackageExportError('');
    try {
      await downloadStrategyPackage(strategyName, { scope: 'bundle' });
    } catch (e) {
      setPackageExportError(e?.message || '导出失败');
    } finally {
      setPackageExporting(false);
    }
  }, [strategyName]);

  const confirmRestoreVersion = useCallback(() => {
    const target = versionMap[pendingVersionId];
    if (!target || !strategyName) {
      setConfirmOpen(false);
      return;
    }
    setIsSavingSettings(true);
    setSaveError('');
    restoreStrategyVersion(strategyName, target.id)
      .then((restoreMeta) => {
        const detail = restoreMeta.detail;
        const res = workbenchPageStateFromVersionDetail(detail, strategyName, configVersions);
        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res?.has_other_versions));
        const snapshot = buildWorkbenchSnapshotFromVersionDetail(detail);
        const wbVerRestore = snapshot.versionId;
        lastRunSyncedVersionRef.current = wbVerRestore;
        const hydrationRestore = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
        const serverSettings = res?.settings || {};
        const incomingMeta = serverSettings?.meta && typeof serverSettings.meta === 'object'
          ? serverSettings.meta
          : {
            name: serverSettings?.name,
            description: serverSettings?.description,
            is_enabled: serverSettings?.is_enabled,
          };
        const mergedSettings = mergeShapeOnly(buildMergeBaseSettings(), {
          ...serverSettings,
          meta: normalizeMeta({ ...incomingMeta, name: strategyName }),
        });
        const wb = wbVerRestore || restoreMeta?.version_id || '';
        suppressDraftDrivenPanelResetRef.current = true;
        setInitialSettings(mergedSettings);
        setStrategyDescription(extractStrategyDescription(mergedSettings));
        setDraftSettings(deepClone(mergedSettings));
        setSelectedConfigVersion(wb);
        setSavedBaselineSettings(deepClone(mergedSettings));
        setAppliedSettings(deepClone(mergedSettings));
        setAppliedVersionId(typeof wb === 'string' && wb.trim() !== '' ? wb.trim() : 'userspace');
        patchSession({
          workbenchSnapshot: snapshot,
          draftSettings: deepClone(mergedSettings),
          appliedSettings: deepClone(mergedSettings),
          executionState: {
            stepStatus: hydrationRestore.stepStatus,
            result: hydrationRestore.result,
            compareVersion: { enum: '', price: '', capital: '' },
            runningStep: '',
            runId: '',
            activeRunId: '',
            lastCompletedWorkbenchVersionId: wbVerRestore,
          },
          panelsResetEpoch: session.panelsResetEpoch,
        });
        setConfirmOpen(false);
      })
      .catch((err) => {
        setSaveError(err?.message || '恢复快照失败');
      })
      .finally(() => {
        setIsSavingSettings(false);
      });
  }, [configVersions, patchSession, pendingVersionId, session.panelsResetEpoch, strategyName, versionMap]);

  const confirmDeployToUserspace = useCallback(() => {
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
  }, [getDraftSettingsForSubmit, strategyName]);

  return {
    strategyName,
    activeStep: session.activeStep,
    initialSettings,
    draftSettings,
    setDraftSettings,
    stepStatus: session.executionState?.stepStatus || {},
    stepProgress: session.stepProgress || {},
    runningStep: session.executionState?.runningStep || '',
    executionBusy,
    runError,
    progressDetail,
    forceEnumerate,
    handleDraftDrivenReset,
    suppressDraftDrivenPanelResetRef,
    strategyDisplayName,
    strategyDescription,
    marketProfileLabel,
    isEnabled: Boolean(draftSettings?.is_enabled ?? initialSettings?.is_enabled),
    currentVersionDisplay,
    isAppliedSettings,
    hasPersistedSnapshot,
    hasOtherVersions,
    restoreDropdownVersions,
    disableMetaActions,
    packageExporting,
    packageExportError,
    setPackageExportError,
    isLoadingSettings,
    settingsError,
    saveError,
    userspaceApplyOk,
    isSavingSettings,
    deployConfirmOpen,
    setDeployConfirmOpen,
    confirmOpen,
    setConfirmOpen,
    pendingVersionId,
    moreVersionsOpen,
    setMoreVersionsOpen,
    versionSearch,
    setVersionSearch,
    versionPickerPage,
    setVersionPickerPage,
    versionPickerFiltered,
    versionPickerSlice,
    versionPickerTotalPages,
    configVersions,
    selectedConfigVersion,
    handleRestoreMenuChange,
    handleExportStrategyPackage,
    closeVersionsDialog,
    requestApplyVersion,
    confirmRestoreVersion,
    confirmDeployToUserspace,
    handleRunCurrentStep,
    setSaveError,
    setUserspaceApplyOk,
    resetSessionForDraftChange,
  };
}
