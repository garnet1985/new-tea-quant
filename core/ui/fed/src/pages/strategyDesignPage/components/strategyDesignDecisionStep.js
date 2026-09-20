import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Box, Button, Snackbar, Stack, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/strategyApi';
import {
  deleteDecisionSession,
  fetchDecisionSessions,
  openDecisionSession,
} from '../../../api/decisionApi';
import InlineLoadingState from '../../../components/inlineLoadingState/inlineLoadingState';
import { DecisionPlaySession } from '../../decisionPage/decisionPlayPage';
import DecisionSessionDialogs from '../../decisionPage/decisionSessionDialogs';
import {
  pickRememberedSession,
  unfinishedSessions,
} from '../../decisionPage/decisionSessionPick';
import { EXECUTION_PANEL_TITLE } from '../../strategyWorkbenchPage/panels/strategyExecutionPanel/executionSectionMeta';
import { isHttpStatusError } from 'services/request';
import { isDecisionStepReady } from '../constants/strategyDesignSteps';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import DecisionReportPanel from '../../decisionPage/decisionReportPanel';

function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

function resolveDecisionVersionId(listedVid, display) {
  const listed = String(listedVid || '').trim();
  if (listed) return listed;
  const shown = String(display || '').trim();
  if (/^v?\d+$/i.test(shown)) return shown;
  return '';
}

function StrategyDesignDecisionStep() {
  const navigate = useNavigate();
  const location = useLocation();
  const wb = useStrategyDesignWorkbenchContext();
  const { session, patchSession } = useStrategyDesignSession();
  const ready = isDecisionStepReady(wb.stepStatus);
  const strategyName = wb.strategyName;
  const [sessionId, setSessionId] = useState('');
  const [versionId, setVersionId] = useState('');
  const [sessions, setSessions] = useState([]);
  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState('');
  const [busy, setBusy] = useState(false);
  const [panel, setPanel] = useState(null);
  const [toast, setToast] = useState('');
  const [reportOpen, setReportOpen] = useState(false);

  const versionQuery = useMemo(
    () => (versionId ? { versionId } : {}),
    [versionId],
  );

  const syncDecisionStep = useCallback((listed) => {
    const done = Boolean(listed?.hasCompleted)
      || (listed?.sessions || []).some((row) => row.status === 'completed');
    const current = session.executionState?.stepStatus || {};
    const next = done ? 'done' : 'idle';
    if (current.decision === next) return;
    patchSession({
      executionState: {
        ...session.executionState,
        stepStatus: { ...current, decision: next },
      },
    });
  }, [patchSession, session.executionState]);

  const applyListed = useCallback((listed, fallbackVid) => {
    const vid = resolveDecisionVersionId(
      listed?.versionId,
      fallbackVid || wb.currentVersionDisplay,
    );
    setVersionId(vid);
    setSessions(listed?.sessions || []);
    syncDecisionStep(listed);
    return { listed, vid };
  }, [syncDecisionStep, wb.currentVersionDisplay]);

  const reloadListed = useCallback(async () => {
    const listed = await fetchDecisionSessions(strategyName, versionQuery);
    return applyListed(listed);
  }, [applyListed, strategyName, versionQuery]);

  useEffect(() => {
    if (!ready || !strategyName) {
      setBooting(false);
      setSessionId('');
      setSessions([]);
      return undefined;
    }
    let cancelled = false;
    setBooting(true);
    setBootError('');
    (async () => {
      try {
        const listed = await fetchDecisionSessions(strategyName);
        if (cancelled) return;
        const { listed: rows, vid } = applyListed(listed);
        const remembered = pickRememberedSession(rows);
        if (remembered) {
          setSessionId(remembered);
          return;
        }
        const snap = await openDecisionSession(strategyName, {
          ...(vid ? { versionId: vid } : {}),
          newSession: true,
        });
        if (cancelled) return;
        setSessionId(String(snap.dmId || ''));
        const again = await fetchDecisionSessions(strategyName, vid ? { versionId: vid } : {});
        if (!cancelled) applyListed(again, vid);
      } catch (err) {
        if (!cancelled) setBootError(errorMessage(err, '无法打开决策模拟'));
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, strategyName, wb.appliedVersionId, wb.currentVersionDisplay, applyListed]);

  const goStep = useCallback((stepKey) => {
    if (!strategyName || !stepKey) return;
    navigate(getStrategyDesignPath(strategyName, stepKey), { state: location.state });
  }, [location.state, navigate, strategyName]);

  const startFresh = useCallback(async () => {
    if (!strategyName || busy) return;
    setBusy(true);
    setBootError('');
    try {
      const snap = await openDecisionSession(strategyName, {
        ...versionQuery,
        newSession: true,
      });
      setSessionId(String(snap.dmId || ''));
      setPanel(null);
      setReportOpen(false);
      await reloadListed();
    } catch (err) {
      setBootError(errorMessage(err, '无法新开一局'));
    } finally {
      setBusy(false);
    }
  }, [busy, reloadListed, strategyName, versionQuery]);

  const handleCompleted = useCallback(() => {
    reloadListed().catch(() => {});
  }, [reloadListed]);

  const selectSession = useCallback((dmId) => {
    const next = String(dmId || '').trim();
    if (!next) return;
    setSessionId(next);
    setPanel(null);
    setReportOpen(false);
  }, []);

  const openContinue = useCallback(async () => {
    if (!strategyName || busy) return;
    setBusy(true);
    try {
      const { listed } = await reloadListed();
      const open = unfinishedSessions(listed.sessions);
      if (open.length === 0) return;
      if (open.length === 1) {
        selectSession(open[0].dmId);
        return;
      }
      setPanel('continue');
    } catch (err) {
      setBootError(errorMessage(err, '无法加载对局'));
    } finally {
      setBusy(false);
    }
  }, [busy, reloadListed, selectSession, strategyName]);

  const openManage = useCallback(async () => {
    if (!strategyName || busy) return;
    setBusy(true);
    try {
      await reloadListed();
      setPanel('manage');
    } catch (err) {
      setBootError(errorMessage(err, '无法加载对局'));
    } finally {
      setBusy(false);
    }
  }, [busy, reloadListed, strategyName]);

  const deleteSession = useCallback(async (row) => {
    if (!strategyName || !row?.dmId) return;
    setBusy(true);
    try {
      await deleteDecisionSession(strategyName, row.dmId, versionQuery);
      setToast(`已删除第 ${row.dmId} 局`);
      const { listed } = await reloadListed();
      if (String(row.dmId) !== String(sessionId)) return;
      const next = pickRememberedSession(listed);
      if (next) {
        setSessionId(next);
        return;
      }
      const snap = await openDecisionSession(strategyName, {
        ...versionQuery,
        newSession: true,
      });
      setSessionId(String(snap.dmId || ''));
      await reloadListed();
    } catch (err) {
      setBootError(errorMessage(err, '删除失败'));
    } finally {
      setBusy(false);
    }
  }, [reloadListed, sessionId, strategyName, versionQuery]);

  const unfinished = useMemo(() => unfinishedSessions(sessions), [sessions]);
  const continueDisabled = busy || unfinished.length === 0
    || (unfinished.length === 1 && String(unfinished[0].dmId) === String(sessionId));

  if (!ready) {
    const enumDone = wb.stepStatus?.enum === 'done';
    const portfolioDone = wb.stepStatus?.portfolio === 'done';
    return (
      <Box className="ntq-design-decision-gate">
        <Alert severity="info" variant="outlined">
          决策模拟依赖「枚举机会」和「投资模拟」都完成。价格回测不是前置条件。
        </Alert>
        <Stack direction="row" spacing={1.5} sx={{ mt: 2 }}>
          {!enumDone ? (
            <Button variant="contained" onClick={() => goStep('enum')}>去枚举机会</Button>
          ) : null}
          {!portfolioDone ? (
            <Button variant={enumDone ? 'contained' : 'outlined'} onClick={() => goStep('portfolio')}>
              去投资模拟
            </Button>
          ) : null}
        </Stack>
      </Box>
    );
  }

  if (booting) {
    return <InlineLoadingState block message="正在打开决策模拟…" />;
  }

  if (bootError && !sessionId) {
    return (
      <Alert severity="error" variant="outlined">
        {bootError}
      </Alert>
    );
  }

  if (!sessionId) {
    return (
      <Alert severity="warning" variant="outlined">
        没有可用的决策对局。
      </Alert>
    );
  }

  return (
    <DecisionPlaySession
      strategyKey={strategyName}
      sessionId={sessionId}
      hideStrategyMeta
      onViewReport={() => setReportOpen(true)}
      onCompleted={handleCompleted}
      render={({ loading, error, inner, hud, snapshot, advancing }) => {
        if (loading) return <InlineLoadingState block message="正在加载对局现场…" />;
        if (error) {
          return (
            <Alert severity="error" variant="outlined">{error}</Alert>
          );
        }
        return (
          <Box className={`ntq-design-decision-step${advancing ? ' is-advancing' : ''}${reportOpen ? ' is-report' : ''}`}>
            <Box className="ntq-design-exec-panel ntq-design-decision-step__exec" data-ntq-help="decision-exec">
              <Box className="ntq-design-exec-panel__title-row">
                <Typography variant="subtitle2" fontWeight={600} className="ntq-design-exec-panel__title">
                  {EXECUTION_PANEL_TITLE} - 决策模拟
                  {snapshot?.dmId ? ` · 第 ${snapshot.dmId} 局` : ''}
                </Typography>
                <Stack
                  direction="row"
                  spacing={1}
                  className="ntq-design-decision-step__actions"
                  data-ntq-help="decision-sessions"
                >
                  {reportOpen ? (
                    <Button
                      type="button"
                      variant="outlined"
                      size="small"
                      onClick={() => setReportOpen(false)}
                    >
                      返回对局
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="outlined"
                    size="small"
                    disabled={continueDisabled}
                    onClick={openContinue}
                  >
                    继续
                  </Button>
                  <Button
                    type="button"
                    variant="outlined"
                    size="small"
                    disabled={busy}
                    onClick={openManage}
                  >
                    管理
                  </Button>
                  <Button
                    type="button"
                    variant="contained"
                    size="small"
                    disabled={busy}
                    onClick={startFresh}
                  >
                    新开一局
                  </Button>
                </Stack>
              </Box>
              {bootError ? (
                <Typography variant="caption" color="error" className="ntq-design-exec-panel__error">
                  {bootError}
                </Typography>
              ) : null}
              <Box className="ntq-design-decision-step__clock">
                {hud}
              </Box>
            </Box>
            {inner}
            {reportOpen ? (
              <Box className="ntq-design-decision-step__report">
                <DecisionReportPanel
                  strategyName={strategyName}
                  versionId={versionId}
                  sessionId={sessionId}
                  sessions={sessions}
                  workbenchSnapshot={session.workbenchSnapshot}
                />
              </Box>
            ) : null}
            <DecisionSessionDialogs
              panel={panel}
              onClose={() => setPanel(null)}
              sessions={sessions}
              currentSessionId={sessionId}
              onSelect={selectSession}
              onDelete={deleteSession}
              busy={busy}
            />
            <Snackbar
              open={Boolean(toast)}
              autoHideDuration={2800}
              onClose={() => setToast('')}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            >
              <Alert severity="info" variant="outlined" onClose={() => setToast('')}>
                {toast}
              </Alert>
            </Snackbar>
          </Box>
        );
      }}
    />
  );
}

export default StrategyDesignDecisionStep;
