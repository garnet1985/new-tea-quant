import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { fetchDecisionReport } from '../../api/decisionApi';
import InlineLoadingState from '../../components/inlineLoadingState/inlineLoadingState';
import { isHttpStatusError } from 'services/request';
import CapitalAllocationReport from '../strategyWorkbenchPage/panels/strategyReportPanel/reports/capitalAllocationReport';
import {
  COMPARE_EMPTY_OTHER_VERSION_ZH,
  COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
} from '../strategyWorkbenchPage/panels/strategyReportPanel/constants/strategyReportConstants';
import { slotFromResultReport } from '../strategyWorkbenchPage/panels/strategyReportPanel/lib/strategyReportSlotResolve';
import { normalizeCapitalMetricsFromSummary } from '../strategyWorkbenchPage/mocks/strategyReportMetrics';
import '../strategyWorkbenchPage/panels/strategyReportPanel/strategyReportPanel.scss';

const PORTFOLIO_COMPARE_ID = 'portfolio';

function errorMessage(err, fallback) {
  if (isHttpStatusError(err) && err.message) return err.message;
  return String(err?.message || fallback);
}

function metricsFromSlot(slot) {
  if (!slot || typeof slot !== 'object') return { capitalMetrics: null, stockRows: [] };
  return {
    capitalMetrics: normalizeCapitalMetricsFromSummary(slot),
    stockRows: Array.isArray(slot.stockRows) ? slot.stockRows : [],
  };
}

export default function DecisionReportPanel({
  strategyName,
  versionId,
  sessionId,
  sessions = [],
  workbenchSnapshot = null,
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [slot, setSlot] = useState(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareId, setCompareId] = useState(PORTFOLIO_COMPARE_ID);
  const [compareSlot, setCompareSlot] = useState(null);
  const [compareError, setCompareError] = useState('');
  const [compareBusy, setCompareBusy] = useState(false);

  const portfolioSlot = useMemo(
    () => slotFromResultReport(workbenchSnapshot?.result_report, 'portfolio'),
    [workbenchSnapshot],
  );

  const completedOthers = useMemo(
    () => (sessions || []).filter(
      (row) => row.status === 'completed' && String(row.dmId) !== String(sessionId),
    ),
    [sessionId, sessions],
  );

  const compareOptions = useMemo(() => {
    const rows = [{ id: PORTFOLIO_COMPARE_ID, label: '投资模拟' }];
    completedOthers.forEach((row) => {
      rows.push({ id: `session:${row.dmId}`, label: `第 ${row.dmId} 局` });
    });
    return rows;
  }, [completedOthers]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !sessionId) {
      setSlot(null);
      setLoading(false);
      return undefined;
    }
    setLoading(true);
    setError('');
    fetchDecisionReport(strategyName, sessionId, versionId ? { versionId } : {})
      .then((msg) => {
        if (cancelled) return;
        setSlot(msg.report);
      })
      .catch((err) => {
        if (cancelled) return;
        setSlot(null);
        setError(errorMessage(err, '无法加载决策报告'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, strategyName, versionId]);

  useEffect(() => {
    if (!compareOpen) {
      setCompareId(PORTFOLIO_COMPARE_ID);
      setCompareSlot(null);
      setCompareError('');
      setCompareBusy(false);
    }
  }, [compareOpen]);

  useEffect(() => {
    let cancelled = false;
    if (!compareOpen) return undefined;
    if (compareId === PORTFOLIO_COMPARE_ID) {
      setCompareBusy(false);
      setCompareError(portfolioSlot ? '' : COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH);
      setCompareSlot(portfolioSlot);
      return undefined;
    }
    const dmId = String(compareId || '').replace(/^session:/, '').trim();
    if (!strategyName || !dmId) {
      setCompareSlot(null);
      return undefined;
    }
    setCompareBusy(true);
    setCompareError('');
    fetchDecisionReport(strategyName, dmId, versionId ? { versionId } : {})
      .then((msg) => {
        if (cancelled) return;
        setCompareSlot(msg.report);
      })
      .catch((err) => {
        if (cancelled) return;
        setCompareSlot(null);
        setCompareError(errorMessage(err, COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH));
      })
      .finally(() => {
        if (!cancelled) setCompareBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [compareId, compareOpen, portfolioSlot, strategyName, versionId]);

  const current = metricsFromSlot(slot);
  const compared = metricsFromSlot(compareSlot);
  const compareLabel = compareOptions.find((row) => row.id === compareId)?.label || '对比';
  const canCompare = Boolean(portfolioSlot) || completedOthers.length > 0;

  if (loading) {
    return <InlineLoadingState block message="正在加载决策报告…" />;
  }
  if (error) {
    return <Alert severity="error" variant="outlined">{error}</Alert>;
  }

  return (
    <Box className="ntq-design-step-report ntq-design-decision-report">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="subtitle2" fontWeight={600}>
          决策模拟报告 · 第 {sessionId} 局
        </Typography>
        {canCompare ? (
          <Button
            type="button"
            variant="outlined"
            size="small"
            className="ntq-attention-btn"
            onClick={() => setCompareOpen(true)}
          >
            对比结果
          </Button>
        ) : null}
      </Stack>
      <CapitalAllocationReport
        title="决策模拟报告"
        hideTitle
        metrics={current.capitalMetrics}
        stockRows={current.stockRows}
      />

      <Dialog open={compareOpen} onClose={() => setCompareOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
            <Typography variant="h6" component="span">对比结果</Typography>
            <TextField
              select
              size="small"
              label="对比对象"
              value={compareId}
              onChange={(event) => setCompareId(event.target.value)}
              sx={{ minWidth: 180 }}
            >
              {compareOptions.map((row) => (
                <MenuItem key={row.id} value={row.id}>{row.label}</MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          <Box className="ntq-report-compare__grid">
            <Box>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                当前局（第 {sessionId} 局）
              </Typography>
              <CapitalAllocationReport
                hideTitle
                metrics={current.capitalMetrics}
                stockRows={current.stockRows}
              />
            </Box>
            <Box>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                {compareLabel}
              </Typography>
              {compareBusy ? (
                <InlineLoadingState block message="正在加载对比报告…" />
              ) : null}
              {compareError ? (
                <Typography variant="body2" color="text.secondary">{compareError}</Typography>
              ) : null}
              {!compareBusy && !compareError && compared.capitalMetrics ? (
                <CapitalAllocationReport
                  hideTitle
                  metrics={compared.capitalMetrics}
                  stockRows={compared.stockRows}
                />
              ) : null}
              {!compareBusy && !compareError && !compared.capitalMetrics && compareId === PORTFOLIO_COMPARE_ID ? (
                <Typography variant="body2" color="text.secondary">
                  {COMPARE_EMPTY_OTHER_VERSION_ZH}
                </Typography>
              ) : null}
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
}
