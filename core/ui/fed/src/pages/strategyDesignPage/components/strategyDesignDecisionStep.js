import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, Stack, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/strategyApi';
import {
  fetchDecisionSessions,
  openDecisionSession,
} from '../../../api/decisionApi';
import InlineLoadingState from '../../../components/inlineLoadingState/inlineLoadingState';
import { DecisionPlaySession } from '../../decisionPage/decisionPlayPage';
import { EXECUTION_PANEL_TITLE } from '../../strategyWorkbenchPage/panels/strategyExecutionPanel/executionSectionMeta';
import { isHttpStatusError } from 'services/request';
import { isDecisionStepReady } from '../constants/strategyDesignSteps';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

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

function pickResumeSession(sessions) {
  const open = (sessions || []).filter((row) => row.status === 'in_progress');
  if (!open.length) return null;
  return [...open].sort((a, b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')))[0];
}

function StrategyDesignDecisionStep() {
  const navigate = useNavigate();
  const location = useLocation();
  const wb = useStrategyDesignWorkbenchContext();
  const ready = isDecisionStepReady(wb.stepStatus);
  const strategyName = wb.strategyName;
  const [sessionId, setSessionId] = useState('');
  const [versionId, setVersionId] = useState('');
  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!ready || !strategyName) {
      setBooting(false);
      setSessionId('');
      return undefined;
    }
    let cancelled = false;
    setBooting(true);
    setBootError('');
    (async () => {
      try {
        const listed = await fetchDecisionSessions(strategyName);
        if (cancelled) return;
        const vid = resolveDecisionVersionId(listed.versionId, wb.currentVersionDisplay);
        setVersionId(vid);
        const resume = pickResumeSession(listed.sessions);
        if (resume?.dmId) {
          setSessionId(String(resume.dmId));
          return;
        }
        const snap = await openDecisionSession(strategyName, {
          ...(vid ? { versionId: vid } : {}),
          newSession: true,
        });
        if (cancelled) return;
        setSessionId(String(snap.dmId || ''));
      } catch (err) {
        if (!cancelled) setBootError(errorMessage(err, '无法打开决策模拟'));
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, strategyName, wb.appliedVersionId, wb.currentVersionDisplay]);

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
        ...(versionId ? { versionId } : {}),
        newSession: true,
      });
      setSessionId(String(snap.dmId || ''));
    } catch (err) {
      setBootError(errorMessage(err, '无法新开一局'));
    } finally {
      setBusy(false);
    }
  }, [busy, strategyName, versionId]);

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
      render={({ loading, error, inner, hud, completed, snapshot, advancing }) => {
        if (loading) return <InlineLoadingState block message="正在加载对局现场…" />;
        if (error) {
          return (
            <Alert severity="error" variant="outlined">{error}</Alert>
          );
        }
        return (
          <Box className={`ntq-design-decision-step${advancing ? ' is-advancing' : ''}`}>
            <Box className="ntq-design-exec-panel ntq-design-decision-step__exec">
              <Box className="ntq-design-exec-panel__title-row">
                <Typography variant="subtitle2" fontWeight={600} className="ntq-design-exec-panel__title">
                  {EXECUTION_PANEL_TITLE} - 决策模拟
                  {snapshot?.dmId ? ` · 第 ${snapshot.dmId} 局` : ''}
                </Typography>
                {completed ? (
                  <Button
                    type="button"
                    variant="contained"
                    size="small"
                    disabled={busy}
                    onClick={startFresh}
                  >
                    新开一局
                  </Button>
                ) : null}
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
          </Box>
        );
      }}
    />
  );
}

export default StrategyDesignDecisionStep;
