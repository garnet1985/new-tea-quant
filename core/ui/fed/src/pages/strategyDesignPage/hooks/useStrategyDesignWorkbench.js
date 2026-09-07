import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  applyStrategySettingsToUserspace,
  downloadStrategyPackage,
  fetchMarketProfileOptions,
  fetchStrategySettings,
  fetchStrategySettingsCurrent,
  fetchStrategyVersionDetail,
  fetchStrategyVersions,
  persistStrategySettings,
  restoreStrategyVersion,
  deleteStrategyVersion,
  setStrategyVersionPinned,
  revealStrategyFolder,
} from '../../../api/strategyApi';
import {
  migrateLegacyStrategySettings,
  stripLegacyStrategySettingsForRun,
} from '../../../utils/stripLegacyStrategySettings';
import { isFingerprintEqual } from '../lib/strategySettingsFingerprint';
import {
  isDraftDirty,
  isSettingsConflictError,
  occupancyFromError,
  persistComparable,
} from '../lib/settingsOccupancy';
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
import logClientError from '../../../utils/logClientError';
import {
  buildWorkbenchSnapshotFromVersionDetail,
  workbenchPageStateFromVersionDetail,
} from '../lib/workbenchPageState';
import { clearDesignActiveRun } from '../lib/strategyDesignActiveRunPersistence';
import { useStrategyDesignSession } from '../strategyDesignContext';
import {
  readCachedStrategyLabel,
  readCachedWorkbenchVersion,
  readStrategyLabelFromLocationState,
  writeCachedStrategyLabel,
  writeCachedWorkbenchVersion,
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

function editorSettingsFromDisk(serverSettings, extraMeta = {}) {
  const src = serverSettings && typeof serverSettings === 'object' ? serverSettings : {};
  const incomingMeta = src.meta && typeof src.meta === 'object' ? src.meta : {};
  return migrateLegacyStrategySettings(mergeShapeOnly(buildMergeBaseSettings(), {
    ...src,
    meta: normalizeMeta({ ...incomingMeta, ...extraMeta }, src),
  }));
}

function mapConfigVersionRows(verRes) {
  return (verRes?.versions || []).map((version) => ({
    id: version.version_id || `v${version.version || ''}`,
    createdAt: version.created_at || '',
    updatedAt: version.updated_at || '',
    version: Number(version.version || 0),
    envInvalid: Boolean(version.env_invalid),
    expiresSoon: Boolean(version.expires_soon),
    pinned: Boolean(version.pinned),
    retentionMax: Number(version.retention_max || 0),
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
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [pendingDeleteVersionId, setPendingDeleteVersionId] = useState('');
  const [isDeletingVersion, setIsDeletingVersion] = useState(false);
  const [isPinningVersion, setIsPinningVersion] = useState(false);
  const [moreVersionsOpen, setMoreVersionsOpen] = useState(false);
  const [packageExporting, setPackageExporting] = useState(false);
  const [packageExportError, setPackageExportError] = useState('');
  const [folderRevealError, setFolderRevealError] = useState('');
  const [diskConflict, setDiskConflict] = useState(null);
  const [diskConflictBusy, setDiskConflictBusy] = useState(false);

  const lastRunSyncedVersionRef = useRef('');
  const snapshotSyncGenRef = useRef(0);
  const pinningLockRef = useRef(false);
  const suppressDraftDrivenPanelResetRef = useRef(false);
  const loadedRevRef = useRef('');
  const loadedSettingsRef = useRef(buildMergeBaseSettings());
  const draftSettingsRef = useRef(buildMergeBaseSettings());
  const occupancyCheckRef = useRef(false);
  const pendingRunAfterOverwriteRef = useRef(null);
  const confirmRestoreVersionRef = useRef(null);
  const executionStateRef = useRef(session.executionState);
  executionStateRef.current = session.executionState;
  draftSettingsRef.current = draftSettings;
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

  const adoptLoadedFill = useCallback((nextSettings, settingsRev) => {
    loadedRevRef.current = String(settingsRev || '');
    loadedSettingsRef.current = deepClone(nextSettings || buildMergeBaseSettings());
  }, []);

  const fillEditorFromDisk = useCallback((serverSettings, settingsRev, extraMeta = {}) => {
    const nextSettings = editorSettingsFromDisk(serverSettings, extraMeta);
    const nextDisplayName = extractStrategyDisplayName(nextSettings);
    const nextKey = extractStrategyKey(nextSettings);
    suppressDraftDrivenPanelResetRef.current = true;
    setInitialSettings(nextSettings);
    setStrategyDisplayName(nextDisplayName);
    setStrategyKey(nextKey);
    if (strategyName) {
      writeCachedStrategyLabel(strategyName, {
        displayName: nextDisplayName,
        key: nextKey,
      });
    }
    setStrategyDescription(extractStrategyDescription(nextSettings));
    setStrategyEntryConditions(extractStrategyEntryConditions(nextSettings));
    setHasValidSettings(true);
    setSettingsError('');
    adoptLoadedFill(nextSettings, settingsRev);
    return nextSettings;
  }, [adoptLoadedFill, strategyName]);

  const adoptPersistedRev = useCallback((settingsRev, draft = draftSettingsRef.current) => {
    loadedRevRef.current = String(settingsRev || '');
    loadedSettingsRef.current = persistComparable(draft);
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
      .then(async ([verRes, res]) => {
        if (isCancelled) return;
        const rows = mapConfigVersionRows(verRes);
        setConfigVersions(rows);
        setHasPersistedSnapshot(Boolean(res?.has_persisted_snapshot));
        setHasOtherVersions(Boolean(res?.has_other_versions));

        const serverSettings = res?.disk_settings || res?.settings || {};
        const hasServerSettings = serverSettings && typeof serverSettings === 'object'
          && Object.keys(serverSettings).length > 0;

        if (hasServerSettings) {
          fillEditorFromDisk(serverSettings, res?.settings_rev);
        } else {
          setInitialSettings(mergeBase);
          adoptLoadedFill(mergeBase, res?.settings_rev);
          setStrategyDescription('');
          setStrategyEntryConditions([]);
          setHasValidSettings(false);
          setSettingsError('未返回有效策略配置（settings 为空）。');
        }

        let snapshot = buildWorkbenchSnapshotFromSettingsResponse(res);
        const latestVer = normalizeWorkbenchVersionId(snapshot.versionId);
        const cachedVer = normalizeWorkbenchVersionId(
          readCachedWorkbenchVersion(strategyName),
        );
        if (cachedVer && cachedVer !== latestVer) {
          try {
            const detail = await fetchStrategyVersionDetail(strategyName, cachedVer);
            if (isCancelled) return;
            snapshot = buildWorkbenchSnapshotFromVersionDetail(detail);
            const flags = workbenchPageStateFromVersionDetail(detail, strategyName, rows);
            setHasPersistedSnapshot(Boolean(flags.has_persisted_snapshot));
            setHasOtherVersions(Boolean(flags.has_other_versions));
          } catch (error) {
            logClientError('design.cachedWorkbenchVersion', error);
          }
        }

        const hydration = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
        const wbVer = normalizeWorkbenchVersionId(snapshot.versionId);
        writeCachedWorkbenchVersion(strategyName, wbVer);
        setSelectedConfigVersion(wbVer);
        setAppliedVersionId(wbVer);
        lastRunSyncedVersionRef.current = hydration.lastCompletedWorkbenchVersionId;

        setSession((prev) => {
          const prevVid = normalizeWorkbenchVersionId(
            prev.executionState?.lastCompletedWorkbenchVersionId,
          );
          const versionChanged = Boolean(prevVid) && prevVid !== wbVer;
          const nextDraft = hasServerSettings
            ? editorSettingsFromDisk(serverSettings)
            : mergeBase;
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
  }, [adoptLoadedFill, fillEditorFromDisk, patchSession, setSession, strategyName]);

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
        writeCachedWorkbenchVersion(strategyName, wbVer);
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

  const currentVersionPinned = useMemo(() => {
    const vid = String(currentVersionDisplay || '').trim();
    const row = configVersions.find((item) => item.id === vid);
    if (row) return Boolean(row.pinned);
    return Boolean(session.workbenchSnapshot?.pinned);
  }, [configVersions, currentVersionDisplay, session.workbenchSnapshot?.pinned]);

  const marketProfileLabel = useMemo(() => {
    const mp = draftSettings?.market_profile || initialSettings?.market_profile || '';
    const row = marketProfileOptions.find((o) => o.value === mp);
    return row?.label || mp || '—';
  }, [draftSettings, initialSettings, marketProfileOptions]);

  const getDraftSettingsForSubmit = useCallback(
    () => stripLegacyStrategySettingsForRun(deepClone(draftSettings)),
    [draftSettings],
  );

  const getSettingsRev = useCallback(() => loadedRevRef.current, []);

  const onSettingsPersisted = useCallback((started) => {
    if (started?.settings_rev != null) {
      adoptPersistedRev(started.settings_rev);
    }
  }, [adoptPersistedRev]);

  const onSettingsConflict = useCallback((err, pendingRun) => {
    pendingRunAfterOverwriteRef.current = pendingRun || null;
    setDiskConflict({
      intent: 'run',
      ...occupancyFromError(err),
    });
  }, []);

  const {
    runError,
    progressDetail,
    handleRunCurrentStep,
    retryRunAfterOverwrite,
    forceEnumerate,
    executionBusy,
  } = useStrategyDesignExecution({
    strategyName,
    activeStep: session.activeStep,
    getDraftSettingsForSubmit,
    getSettingsRev,
    setAppliedSettings,
    isLoadingSettings,
    onRunStarted,
    onSettingsPersisted,
    onSettingsConflict,
    setSession,
    getExecutionState,
  });

  const disableMetaActions = isSavingSettings || isDeletingVersion || isLoadingSettings || !hasValidSettings || !strategyName || executionBusy;
  const disablePinActions = isPinningVersion || isLoadingSettings || !strategyName || executionBusy;

  const handleSettingsFocus = useCallback(() => {
    if (!strategyName || isLoadingSettings || executionBusy || diskConflict || occupancyCheckRef.current) {
      return;
    }
    occupancyCheckRef.current = true;
    fetchStrategySettingsCurrent(strategyName)
      .then((occupancy) => {
        const remoteRev = String(occupancy?.settings_rev || '');
        if (remoteRev === loadedRevRef.current) return;
        if (isDraftDirty(draftSettingsRef.current, loadedSettingsRef.current)) {
          setDiskConflict({ intent: 'focus', ...occupancy });
          return;
        }
        fillEditorFromDisk(occupancy.disk_settings, occupancy.settings_rev);
        setRestoreOk('已从 settings.py 刷新');
        setSaveError('');
      })
      .catch((err) => {
        logClientError('design.settingsOccupancy', err);
      })
      .finally(() => {
        occupancyCheckRef.current = false;
      });
  }, [diskConflict, executionBusy, fillEditorFromDisk, isLoadingSettings, strategyName]);

  const closeDiskConflict = useCallback(() => {
    setDiskConflict(null);
    setDiskConflictBusy(false);
    pendingRunAfterOverwriteRef.current = null;
  }, []);

  const confirmDiskConflictTakeFile = useCallback(() => {
    if (!diskConflict) return;
    fillEditorFromDisk(diskConflict.disk_settings, diskConflict.settings_rev);
    setRestoreOk('已用 settings.py 覆盖编辑器');
    setSaveError('');
    closeDiskConflict();
  }, [closeDiskConflict, diskConflict, fillEditorFromDisk]);

  const confirmDiskConflictOverwriteFile = useCallback(async () => {
    if (!diskConflict || !strategyName) return;
    const intent = diskConflict.intent;
    setDiskConflictBusy(true);
    setSaveError('');
    try {
      if (intent === 'restore') {
        setDiskConflict(null);
        setDiskConflictBusy(false);
        confirmRestoreVersionRef.current?.({ skipOccupancyCheck: true, force: true });
        return;
      }
      if (intent === 'run') {
        const pendingRun = pendingRunAfterOverwriteRef.current;
        closeDiskConflict();
        if (pendingRun) retryRunAfterOverwrite(pendingRun);
        return;
      }
      const payload = getDraftSettingsForSubmit();
      const occupancy = await persistStrategySettings(strategyName, payload, {
        settings_rev: loadedRevRef.current,
        force: true,
      });
      adoptPersistedRev(occupancy.settings_rev, payload);
      setRestoreOk('已用编辑器覆盖 settings.py');
      closeDiskConflict();
    } catch (err) {
      setDiskConflictBusy(false);
      if (isSettingsConflictError(err)) {
        setDiskConflict((prev) => (prev ? { ...prev, ...occupancyFromError(err) } : prev));
        return;
      }
      setSaveError(err?.message || '写回 settings.py 失败');
    }
  }, [
    adoptPersistedRev,
    closeDiskConflict,
    diskConflict,
    getDraftSettingsForSubmit,
    retryRunAfterOverwrite,
    strategyName,
  ]);

  const handleDraftDrivenReset = useCallback(() => {
    if (strategyName) clearDesignActiveRun(strategyName);
  }, [strategyName]);

  const requestApplyVersion = useCallback((versionId) => {
    if (!versionId) return;
    setPendingVersionId(versionId);
    setConfirmOpen(true);
  }, []);

  const requestDeleteVersion = useCallback((versionId) => {
    if (!versionId) return;
    setPendingDeleteVersionId(versionId);
    setDeleteConfirmOpen(true);
  }, []);

  const toggleVersionPinned = useCallback(async (versionId) => {
    const targetId = normalizeWorkbenchVersionId(versionId);
    if (!targetId || !strategyName || pinningLockRef.current) return;
    const current = configVersions.find((row) => row.id === targetId);
    const currentlyPinned = Boolean(current?.pinned);
    const nextPinned = !currentlyPinned;
    pinningLockRef.current = true;
    setIsPinningVersion(true);
    setSaveError('');
    setConfigVersions((prev) => {
      const next = prev.map((row) => (
        row.id === targetId
          ? { ...row, pinned: nextPinned, expiresSoon: nextPinned ? false : row.expiresSoon }
          : row
      ));
      return [...next.filter((row) => row.pinned), ...next.filter((row) => !row.pinned)];
    });
    try {
      await setStrategyVersionPinned(strategyName, targetId, nextPinned);
      const verRes = await fetchStrategyVersions(strategyName);
      setConfigVersions(mapConfigVersionRows(verRes));
    } catch (err) {
      try {
        const verRes = await fetchStrategyVersions(strategyName);
        setConfigVersions(mapConfigVersionRows(verRes));
      } catch (reloadErr) {
        setConfigVersions((prev) => prev.map((row) => (
          row.id === targetId ? { ...row, pinned: currentlyPinned } : row
        )));
        logClientError('design.reloadVersionsAfterPin', reloadErr);
      }
      setSaveError(err?.message || (nextPinned ? '固定失败' : '取消固定失败'));
    } finally {
      pinningLockRef.current = false;
      setIsPinningVersion(false);
    }
  }, [configVersions, strategyName]);

  const confirmDeleteVersion = useCallback(async () => {
    const targetId = normalizeWorkbenchVersionId(pendingDeleteVersionId);
    if (!targetId || !strategyName) {
      setDeleteConfirmOpen(false);
      return;
    }
    setIsDeletingVersion(true);
    setSaveError('');
    setRestoreOk('');
    try {
      await deleteStrategyVersion(strategyName, targetId);
      const verRes = await fetchStrategyVersions(strategyName);
      const rows = mapConfigVersionRows(verRes);
      setConfigVersions(rows);
      const deletedWasCurrent = [
        selectedConfigVersion,
        appliedVersionId,
        lastCompletedId,
      ].some((id) => normalizeWorkbenchVersionId(id) === targetId);
      const nextId = rows[0]?.id || '';
      if (deletedWasCurrent) {
        if (nextId) {
          const detail = await fetchStrategyVersionDetail(strategyName, nextId);
          const snapshot = buildWorkbenchSnapshotFromVersionDetail(detail);
          const flags = workbenchPageStateFromVersionDetail(detail, strategyName, rows);
          setHasPersistedSnapshot(Boolean(flags.has_persisted_snapshot));
          setHasOtherVersions(Boolean(flags.has_other_versions));
          const hydration = buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot);
          const wbVer = normalizeWorkbenchVersionId(snapshot.versionId);
          writeCachedWorkbenchVersion(strategyName, wbVer);
          setSelectedConfigVersion(wbVer);
          setAppliedVersionId(wbVer);
          lastRunSyncedVersionRef.current = hydration.lastCompletedWorkbenchVersionId;
          patchSession({
            workbenchSnapshot: snapshot,
            executionState: {
              stepStatus: mergeHydratedStepStatus(
                session.executionState?.stepStatus,
                hydration.stepStatus,
                { versionChanged: true },
              ),
              result: hydration.result,
              compareVersion: { enum: '', price: '', portfolio: '' },
              runningStep: '',
              runId: '',
              activeRunId: '',
              lastCompletedWorkbenchVersionId: hydration.lastCompletedWorkbenchVersionId,
            },
          });
        } else {
          writeCachedWorkbenchVersion(strategyName, '');
          setSelectedConfigVersion('');
          setAppliedVersionId('');
          setHasPersistedSnapshot(false);
          setHasOtherVersions(false);
          lastRunSyncedVersionRef.current = '';
          setMoreVersionsOpen(false);
          patchSession({
            workbenchSnapshot: emptyWorkbenchSnapshot(),
            executionState: {
              stepStatus: { enum: 'idle', price: 'idle', portfolio: 'idle' },
              result: { enum: null, price: null, portfolio: null },
              compareVersion: { enum: '', price: '', portfolio: '' },
              runningStep: '',
              runId: '',
              activeRunId: '',
              lastCompletedWorkbenchVersionId: '',
            },
          });
        }
      } else {
        setHasPersistedSnapshot(rows.length > 0);
        setHasOtherVersions(rows.length >= 2);
      }
      setDeleteConfirmOpen(false);
      setPendingDeleteVersionId('');
      setRestoreOk(`已删除 ${targetId} 的回测产物`);
    } catch (err) {
      setSaveError(err?.message || '删除失败');
    } finally {
      setIsDeletingVersion(false);
    }
  }, [
    appliedVersionId,
    lastCompletedId,
    patchSession,
    pendingDeleteVersionId,
    selectedConfigVersion,
    session.executionState?.stepStatus,
    strategyName,
  ]);

  const openMoreVersionsDialog = useCallback(() => {
    setSaveError('');
    setRestoreOk('');
    setMoreVersionsOpen(true);
  }, []);

  const closeVersionsDialog = useCallback(() => {
    setMoreVersionsOpen(false);
  }, []);

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

  const handleRevealStrategyFolder = useCallback(async () => {
    if (!strategyName) return;
    setFolderRevealError('');
    try {
      await revealStrategyFolder(strategyName);
    } catch (e) {
      setFolderRevealError(e?.message || '无法打开文件夹');
    }
  }, [strategyName]);

  const confirmRestoreVersion = useCallback(async (opts = {}) => {
    const target = versionMap[pendingVersionId];
    if (!target || !strategyName) {
      setConfirmOpen(false);
      return;
    }
    const skipOccupancyCheck = Boolean(opts.skipOccupancyCheck);
    const forceWrite = Boolean(opts.force);
    setIsSavingSettings(true);
    setSaveError('');
    setRestoreOk('');
    try {
      if (!skipOccupancyCheck) {
        const occupancy = await fetchStrategySettingsCurrent(strategyName);
        const remoteRev = String(occupancy.settings_rev || '');
        const dirty = isDraftDirty(draftSettingsRef.current, loadedSettingsRef.current);
        if (dirty && remoteRev !== loadedRevRef.current) {
          setDiskConflict({ intent: 'restore', ...occupancy });
          return;
        }
        if (!dirty && remoteRev !== loadedRevRef.current) {
          opts = { ...opts, force: true };
        }
      }
      const applied = await applyStrategySettingsToUserspace(strategyName, null, {
        version_id: target.id,
        settings_rev: loadedRevRef.current,
        force: forceWrite || Boolean(opts.force) || skipOccupancyCheck,
      });
      const restoreMeta = await restoreStrategyVersion(strategyName, target.id);
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
      const mergedSettings = fillEditorFromDisk(
        serverSettings,
        applied.settings_rev || detail.settings_rev,
        { name: strategyName },
      );
      const wb = wbVerRestore || restoreMeta?.version_id || '';
      writeCachedWorkbenchVersion(strategyName, wb);
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
      setDiskConflict(null);
    } catch (err) {
      if (isSettingsConflictError(err)) {
        setDiskConflict({ intent: 'restore', ...occupancyFromError(err) });
        return;
      }
      setSaveError(err?.message || '恢复配置失败');
    } finally {
      setIsSavingSettings(false);
    }
  }, [
    configVersions,
    fillEditorFromDisk,
    patchSession,
    pendingVersionId,
    session.panelsResetEpoch,
    strategyName,
    versionMap,
  ]);
  confirmRestoreVersionRef.current = confirmRestoreVersion;

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
    currentVersionPinned,
    isAppliedSettings,
    envInvalid,
    capsuleStatus,
    hasPersistedSnapshot,
    hasOtherVersions,
    disableMetaActions,
    disablePinActions,
    packageExporting,
    packageExportError,
    folderRevealError,
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
    deleteConfirmOpen,
    setDeleteConfirmOpen,
    pendingDeleteVersionId,
    isDeletingVersion,
    isPinningVersion,
    moreVersionsOpen,
    setMoreVersionsOpen,
    configVersions,
    selectedConfigVersion,
    openMoreVersionsDialog,
    handleExportStrategyPackage,
    handleRevealStrategyFolder,
    closeVersionsDialog,
    requestApplyVersion,
    requestDeleteVersion,
    toggleVersionPinned,
    confirmDeleteVersion,
    confirmRestoreVersion,
    handleRunCurrentStep,
    handleSettingsFocus,
    diskConflict,
    diskConflictBusy,
    closeDiskConflict,
    confirmDiskConflictTakeFile,
    confirmDiskConflictOverwriteFile,
    setSaveError,
    setRestoreOk,
    resetSessionForDraftChange,
  };
}
