import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  applyStrategySettingsToUserspace,
  downloadStrategyPackage,
  fetchMarketProfileOptions,
  fetchStrategySettings,
  fetchStrategyVersionDetail,
  fetchStrategyVersions,
  restoreStrategyVersion,
} from '../../../api/strategyApi';
import {
  migrateLegacyStrategySettings,
  stripLegacyStrategySettingsForRun,
} from '../../../utils/stripLegacyStrategySettings';
import { isFingerprintEqual } from '../lib/strategySettingsFingerprint';
import {
  extractStrategyDescription,
  extractStrategyDisplayName,
  extractStrategyEntryConditions,
  extractStrategyKey,
  normalizeMeta,
} from '../../strategyWorkbenchPage/panels/strategySettingsPanel/editorSchemas/strategyMeta';
import {
  buildWorkbenchExecutionHydrationFromSnapshot,
  mergeHydratedStepStatus,
} from '../../strategyWorkbenchPage/workbenchExecutionHydration';
import { normalizeWorkbenchVersionId, parseWorkbenchVersionNumber } from '../../../utils/workbenchVersionId';
import {
  buildWorkbenchSnapshotFromSettingsResponse,
  emptyWorkbenchSnapshot,
} from '../../strategyWorkbenchPage/workbenchSnapshot';
import { DESIGN_RESTORE_MORE_MENU_VALUE, VERSION_PICKER_PAGE_SIZE } from '../constants/strategyDesignMetaConstants';
import logClientError from '../../../utils/logClientError';
import {
  buildWorkbenchSnapshotFromVersionDetail,
  workbenchPageStateFromVersionDetail,
} from '../lib/workbenchPageState';
import { clearDesignActiveRun } from '../lib/strategyDesignActiveRunPersistence';
import { useStrategyDesignSession } from '../strategyDesignContext';
import {
  readCachedStrategyLabel,
  readStrategyLabelFromLocationState,
  writeCachedStrategyLabel,
} from '../strategyDesignSessionState';
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
    envInvalid: Boolean(version.env_invalid),
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
  const location = useLocation();

  const labelSeed = useMemo(() => {
    const fromNav = readStrategyLabelFromLocationState(location.state);
    const fromCache = readCachedStrategyLabel(strategyName);
    return {
      displayName: fromNav.displayName || fromCache.displayName || '',
      key: fromNav.key || fromCache.key || '',
    };
  }, [location.state, strategyName]);

  const [configVersions, setConfigVersions] = useState([]);
  const [hasPersistedSnapshot, setHasPersistedSnapshot] = useState(false);
  const [hasOtherVersions, setHasOtherVersions] = useState(false);
  const [isLoadingSettings, setIsLoadingSettings] = useState(true);
  const [hasValidSettings, setHasValidSettings] = useState(false);
  const [settingsError, setSettingsError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [restoreOk, setRestoreOk] = useState('');
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [strategyDisplayName, setStrategyDisplayName] = useState(() => labelSeed.displayName);
  const [strategyKey, setStrategyKey] = useState(() => labelSeed.key);
  const [strategyDescription, setStrategyDescription] = useState('');
  const [strategyEntryConditions, setStrategyEntryConditions] = useState([]);
  const [initialSettings, setInitialSettings] = useState(() => buildMergeBaseSettings());
  const [draftSettings, setDraftSettings] = useState(() => buildMergeBaseSettings());
  const [appliedSettings, setAppliedSettings] = useState(() => buildMergeBaseSettings());
  const [selectedConfigVersion, setSelectedConfigVersion] = useState('');
  const [appliedVersionId, setAppliedVersionId] = useState('');
  const [marketProfileOptions, setMarketProfileOptions] = useState([]);
  const [marketProfileOptionsError, setMarketProfileOptionsError] = useState('');

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
  const labelSeedRef = useRef(labelSeed);
  labelSeedRef.current = labelSeed;

  const lastCompletedId = String(session.executionState?.lastCompletedWorkbenchVersionId || '').trim();
  const runIsActive = Boolean(
    session.executionState?.activeRunId || session.executionState?.runningStep,
  );

  const getExecutionState = useCallback(() => executionStateRef.current, []);

  const onRunStarted = useCallback(() => {
    lastRunSyncedVersionRef.current = '';
    snapshotSyncGenRef.current += 1;
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchMarketProfileOptions()
      .then((rows) => {
        if (!cancelled) {
          setMarketProfileOptions(Array.isArray(rows) ? rows : []);
          setMarketProfileOptionsError('');
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setMarketProfileOptions([]);
          setMarketProfileOptionsError(err?.message || '市场配置选项加载失败');
          logClientError('design.marketProfileOptions', err);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setAppliedSettings(deepClone(initialSettings));
    setDraftSettings(deepClone(initialSettings));
  }, [initialSettings]);

  useEffect(() => {
    let isCancelled = false;
    const mergeBase = buildMergeBaseSettings();
    const seed = labelSeedRef.current;

    if (!strategyName) {
      setIsLoadingSettings(false);
      return undefined;
    }

    setStrategyDescription('');
    setStrategyEntryConditions([]);
    // 用导航 state / session 种子，加载完成前不闪路径名
    setStrategyDisplayName(seed.displayName);
    setStrategyKey(seed.key);
    setIsLoadingSettings(true);
    setHasValidSettings(false);
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

        const serverSettings = res?.disk_settings || res?.settings || {};
        const hasServerSettings = serverSettings && typeof serverSettings === 'object'
          && Object.keys(serverSettings).length > 0;
        const incomingMeta = serverSettings?.meta && typeof serverSettings.meta === 'object'
          ? serverSettings.meta
          : {};

        if (hasServerSettings) {
          const nextSettings = migrateLegacyStrategySettings(mergeShapeOnly(mergeBase, {
            ...serverSettings,
            meta: normalizeMeta(incomingMeta, serverSettings),
          }));
          const nextDisplayName = extractStrategyDisplayName(nextSettings);
          const nextKey = extractStrategyKey(nextSettings);
          setInitialSettings(nextSettings);
          setStrategyDisplayName(nextDisplayName);
          setStrategyKey(nextKey);
          writeCachedStrategyLabel(strategyName, {
            displayName: nextDisplayName,
            key: nextKey,
          });
          setStrategyDescription(extractStrategyDescription(nextSettings));
          setStrategyEntryConditions(extractStrategyEntryConditions(nextSettings));
          setHasValidSettings(true);
          setSettingsError('');
        } else {
          setInitialSettings(mergeBase);
          setStrategyDescription('');
          setStrategyEntryConditions([]);
          setHasValidSettings(false);
          setSettingsError('未返回有效策略配置（settings 为空）。');
        }

        const snapshot = buildWorkbenchSnapshotFromSettingsResponse(res);
        const hydration = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
        const wbVer = normalizeWorkbenchVersionId(snapshot.versionId);
        setSelectedConfigVersion(wbVer);
        setAppliedVersionId(wbVer);
        lastRunSyncedVersionRef.current = hydration.lastCompletedWorkbenchVersionId;

        setSession((prev) => {
          const prevVid = normalizeWorkbenchVersionId(
            prev.executionState?.lastCompletedWorkbenchVersionId,
          );
          const versionChanged = Boolean(prevVid) && prevVid !== wbVer;
          const nextDraft = hasServerSettings ? migrateLegacyStrategySettings(mergeShapeOnly(mergeBase, {
            ...serverSettings,
            meta: normalizeMeta(incomingMeta, serverSettings),
          })) : mergeBase;
          return {
            ...prev,
            workbenchSnapshot: snapshot,
            draftSettings: nextDraft,
            appliedSettings: nextDraft,
            executionState: {
              stepStatus: mergeHydratedStepStatus(
                prev.executionState?.stepStatus,
                hydration.stepStatus,
                { versionChanged: !prevVid || versionChanged },
              ),
              result: hydration.result,
              compareVersion: { enum: '', price: '', portfolio: '' },
              runningStep: '',
              runId: '',
              activeRunId: '',
              lastCompletedWorkbenchVersionId: hydration.lastCompletedWorkbenchVersionId,
            },
            lastUpdatedAt: Date.now(),
          };
        });
      })
      .catch((err) => {
        if (isCancelled) return;
        setInitialSettings(mergeBase);
        setHasPersistedSnapshot(false);
        setHasOtherVersions(false);
        setConfigVersions([]);
        setHasValidSettings(false);
        setSettingsError(err?.message || '读取策略配置失败');
        patchSession({ workbenchSnapshot: emptyWorkbenchSnapshot() });
      })
      .finally(() => {
        if (!isCancelled) setIsLoadingSettings(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [patchSession, setSession, strategyName]);

  useEffect(() => {
    if (!strategyName || isLoadingSettings || runIsActive) return undefined;
    const runVer = lastCompletedId;
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
        const wbVer = normalizeWorkbenchVersionId(res.workbench_version_id || runVer);
        const incomingN = parseWorkbenchVersionNumber(wbVer);

        const live = executionStateRef.current;
        const curVid = normalizeWorkbenchVersionId(live?.lastCompletedWorkbenchVersionId);
        const curN = parseWorkbenchVersionNumber(curVid);
        if (curN > 0 && incomingN > 0 && curN > incomingN) return;
        if (live?.activeRunId || live?.runningStep) return;

        setHasPersistedSnapshot(Boolean(res.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res.has_other_versions));
        setSelectedConfigVersion(wbVer);
        setAppliedVersionId(wbVer);
        lastRunSyncedVersionRef.current = wbVer;
        setSession((prev) => {
          const prevVid = normalizeWorkbenchVersionId(
            prev.executionState?.lastCompletedWorkbenchVersionId,
          );
          const prevN = parseWorkbenchVersionNumber(prevVid);
          if (prevN > 0 && incomingN > 0 && prevN > incomingN) return prev;
          if (prev.executionState?.activeRunId || prev.executionState?.runningStep) return prev;
          const versionChanged = Boolean(prevVid) && prevVid !== wbVer;
          return {
            ...prev,
            workbenchSnapshot: snapshot,
            executionState: {
              ...prev.executionState,
              stepStatus: mergeHydratedStepStatus(
                prev.executionState?.stepStatus,
                hydration.stepStatus,
                { versionChanged },
              ),
              result: hydration.result,
              lastCompletedWorkbenchVersionId: wbVer || prevVid,
            },
            lastUpdatedAt: Date.now(),
          };
        });
      } catch (error) {
        logClientError('design.workbenchSnapshotSync', error);
        setSaveError('工作台数据同步失败，请刷新页面或重新选择版本。');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    isLoadingSettings,
    lastCompletedId,
    runIsActive,
    setSession,
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

  const isAppliedSettings = useMemo(() => {
    const freeze = session.workbenchSnapshot?.effectiveSettings;
    const baseline = (freeze && typeof freeze === 'object' && Object.keys(freeze).length > 0)
      ? freeze
      : (session.workbenchSnapshot?.settings || appliedSettings);
    return isFingerprintEqual(draftSettings, baseline);
  }, [
    appliedSettings,
    draftSettings,
    session.workbenchSnapshot?.effectiveSettings,
    session.workbenchSnapshot?.settings,
  ]);

  const envInvalid = Boolean(session.workbenchSnapshot?.envInvalid);

  const capsuleStatus = envInvalid
    ? '环境已更新'
    : (isAppliedSettings ? '无设置变化' : '设置已变更');

  const currentVersionDisplay = useMemo(() => {
    const applied = String(appliedVersionId || '').trim();
    if (!applied) return 'settings文件';
    return applied;
  }, [appliedVersionId]);

  const marketProfileLabel = useMemo(() => {
    const mp = draftSettings?.market_profile || initialSettings?.market_profile || '';
    const row = marketProfileOptions.find((o) => o.value === mp);
    return row?.label || mp || '—';
  }, [draftSettings, initialSettings, marketProfileOptions]);

  const getDraftSettingsForSubmit = useCallback(
    () => stripLegacyStrategySettingsForRun(deepClone(draftSettings)),
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

  const disableMetaActions = isSavingSettings || isLoadingSettings || !hasValidSettings || !strategyName || executionBusy;

  const handleDraftDrivenReset = useCallback(() => {
    if (strategyName) clearDesignActiveRun(strategyName);
  }, [strategyName]);

  const requestApplyVersion = useCallback((versionId) => {
    if (!versionId) return;
    setPendingVersionId(versionId);
    setConfirmOpen(true);
  }, []);

  const openMoreVersionsDialog = useCallback(() => {
    setSaveError('');
    setRestoreOk('');
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
        setRestoreOk('');
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
    setRestoreOk('');
    applyStrategySettingsToUserspace(strategyName, null, { version_id: target.id })
      .then(() => restoreStrategyVersion(strategyName, target.id))
      .then((restoreMeta) => {
        const detail = restoreMeta.detail;
        const res = workbenchPageStateFromVersionDetail(detail, strategyName, configVersions);
        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res?.has_other_versions));
        const snapshot = buildWorkbenchSnapshotFromVersionDetail(detail);
        const wbVerRestore = snapshot.versionId;
        lastRunSyncedVersionRef.current = wbVerRestore;
        const hydrationRestore = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
        const serverSettings = (detail?.settings && Object.keys(detail.settings).length > 0)
          ? detail.settings
          : (detail?.disk_settings && Object.keys(detail.disk_settings).length > 0)
            ? detail.disk_settings
            : (res?.settings || {});
        const incomingMeta = serverSettings?.meta && typeof serverSettings.meta === 'object'
          ? serverSettings.meta
          : {
            name: serverSettings?.name,
            description: serverSettings?.description,
            is_enabled: serverSettings?.is_enabled,
          };
        const mergedSettings = migrateLegacyStrategySettings(mergeShapeOnly(buildMergeBaseSettings(), {
          ...serverSettings,
          meta: normalizeMeta({ ...incomingMeta, name: strategyName }),
        }));
        const wb = wbVerRestore || restoreMeta?.version_id || '';
        suppressDraftDrivenPanelResetRef.current = true;
        setInitialSettings(mergedSettings);
        const restoredDisplayName = extractStrategyDisplayName(mergedSettings);
        const restoredKey = extractStrategyKey(mergedSettings);
        setStrategyDisplayName(restoredDisplayName);
        setStrategyKey(restoredKey);
        writeCachedStrategyLabel(strategyName, {
          displayName: restoredDisplayName,
          key: restoredKey,
        });
        setStrategyDescription(extractStrategyDescription(mergedSettings));
        setStrategyEntryConditions(extractStrategyEntryConditions(mergedSettings));
        setHasValidSettings(true);
        setDraftSettings(deepClone(mergedSettings));
        setSelectedConfigVersion(wb);
        setAppliedSettings(deepClone(mergedSettings));
        setAppliedVersionId(typeof wb === 'string' ? wb.trim() : '');
        patchSession({
          workbenchSnapshot: snapshot,
          draftSettings: deepClone(mergedSettings),
          appliedSettings: deepClone(mergedSettings),
          executionState: {
            stepStatus: hydrationRestore.stepStatus,
            result: hydrationRestore.result,
            compareVersion: { enum: '', price: '', portfolio: '' },
            runningStep: '',
            runId: '',
            activeRunId: '',
            lastCompletedWorkbenchVersionId: wbVerRestore,
          },
          panelsResetEpoch: session.panelsResetEpoch,
        });
        setRestoreOk('已将历史配置写回 settings.py。');
        setConfirmOpen(false);
      })
      .catch((err) => {
        setSaveError(err?.message || '恢复配置失败');
      })
      .finally(() => {
        setIsSavingSettings(false);
      });
  }, [configVersions, patchSession, pendingVersionId, session.panelsResetEpoch, strategyName, versionMap]);

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
    strategyKey,
    strategyDescription,
    strategyEntryConditions,
    marketProfileLabel,
    marketProfileOptionsError,
    isEnabled: Boolean(draftSettings?.is_enabled ?? initialSettings?.is_enabled),
    currentVersionDisplay,
    isAppliedSettings,
    envInvalid,
    capsuleStatus,
    hasPersistedSnapshot,
    hasOtherVersions,
    restoreDropdownVersions,
    disableMetaActions,
    packageExporting,
    packageExportError,
    setPackageExportError,
    isLoadingSettings,
    hasValidSettings,
    settingsError,
    saveError,
    restoreOk,
    isSavingSettings,
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
    handleRunCurrentStep,
    setSaveError,
    setRestoreOk,
    resetSessionForDraftChange,
  };
}
