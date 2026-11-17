import React, { useEffect, useMemo, useState } from 'react';
import { fetchDecisionReport } from '../../api/decisionApi';
import { Loading } from 'ui';
import { Button, Dialog, Message, Select } from 'ui';
import { isHttpStatusError } from 'service/request';
import {
  COMPARE_EMPTY_OTHER_VERSION_ZH,
  COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
  CapitalAllocationReport,
  normalizeCapitalMetricsFromSummary,
  slotFromResultReport,
} from 'containers/strategyReport';
import './decisionReportPanel.scss';

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
    const rows = [{ value: PORTFOLIO_COMPARE_ID, label: '投资模拟' }];
    completedOthers.forEach((row) => {
      rows.push({ value: `session:${row.dmId}`, label: `模拟回测 #${row.dmId}` });
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
  const compareLabel = compareOptions.find((row) => row.value === compareId)?.label || '对比';
  const canCompare = Boolean(portfolioSlot) || completedOthers.length > 0;

  if (loading) {
    return <Loading variant="inline" message="正在加载决策报告…" className="is-block" />;
  }
  if (error) {
    return <Message status="error">{error}</Message>;
  }

  return (
    <div className="ntq-design-step-report ntq-design-decision-report">
      <div className="ntq-design-decision-report__head">
        <h3 className="ntq-design-decision-report__title">
          决策模拟回测报告 · #{sessionId}
        </h3>
        {canCompare ? (
          <Button
            type="button"
            variant="attention"
            onClick={() => setCompareOpen(true)}
          >
            对比结果
          </Button>
        ) : null}
      </div>
      <CapitalAllocationReport
        title="决策模拟报告"
        hideTitle
        metrics={current.capitalMetrics}
        stockRows={current.stockRows}
      />

      <Dialog
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        size="lg"
        title={(
          <span className="ntq-design-decision-report__compare-title">
            <span>对比结果</span>
            <Select
              label="对比对象"
              labelPlacement="none"
              maxWidth={false}
              className="ntq-design-decision-report__compare-select"
              value={compareId}
              options={compareOptions}
              onChange={(e) => setCompareId(e.target.value)}
              aria-label="对比对象"
            />
          </span>
        )}
      >
        <div className="ntq-report-compare__grid">
          <div>
            <h4 className="ntq-design-decision-report__col-title">
              当前模拟回测（#{sessionId}）
            </h4>
            <CapitalAllocationReport
              hideTitle
              metrics={current.capitalMetrics}
              stockRows={current.stockRows}
            />
          </div>
          <div>
            <h4 className="ntq-design-decision-report__col-title">
              {compareLabel}
            </h4>
            {compareBusy ? (
              <Loading variant="inline" message="正在加载对比报告…" className="is-block" />
            ) : null}
            {compareError ? (
              <p className="ntq-muted">{compareError}</p>
            ) : null}
            {!compareBusy && !compareError && compared.capitalMetrics ? (
              <CapitalAllocationReport
                hideTitle
                metrics={compared.capitalMetrics}
                stockRows={compared.stockRows}
              />
            ) : null}
            {!compareBusy && !compareError && !compared.capitalMetrics && compareId === PORTFOLIO_COMPARE_ID ? (
              <p className="ntq-muted">
                {COMPARE_EMPTY_OTHER_VERSION_ZH}
              </p>
            ) : null}
          </div>
        </div>
      </Dialog>
    </div>
  );
}
