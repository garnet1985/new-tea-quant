import { useEffect, useMemo, useState } from 'react';
import {
  fetchStrategyStepReport,
  fetchStrategyStepReportRef,
} from '../../../../../api/apis/strategyApi';
import { STEP_TABS } from '../constants/strategyReportConstants';
import {
  ENUM_REF_DEFAULT_SORT,
  mapStockRefToRows,
  sortMappedEnumRows,
} from '../lib/strategyReportEnumRef';

/**
 * V2-07 单步 report、枚举 report_ref；由 ``executionState.stepStatus`` 推导可用 Tab。
 */
export function useStrategyReportRemoteData({
  strategyName,
  reportVersionId,
  activeTab,
  executionState,
}) {
  const versionIdForReport = String(reportVersionId || '').trim();
  const [reportStocks] = useState({ enum: [], price: [], capital: [] });
  const [enumRefStatus, setEnumRefStatus] = useState('idle');
  const [enumRefRows, setEnumRefRows] = useState([]);
  const [stepReportSlots, setStepReportSlots] = useState({
    enum: null,
    price: null,
    capital: null,
  });

  const availableTabs = useMemo(() => {
    const stepStatus = executionState?.stepStatus || {};
    return STEP_TABS.filter((tab) => stepStatus[tab.key] === 'done');
  }, [executionState]);

  const resolvedActiveTab = useMemo(() => {
    if (availableTabs.length === 0) return '';
    if (availableTabs.some((tab) => tab.key === activeTab)) return activeTab;
    return availableTabs[availableTabs.length - 1].key;
  }, [activeTab, availableTabs]);

  useEffect(() => {
    if (!versionIdForReport) {
      setStepReportSlots({ enum: null, price: null, capital: null });
    }
  }, [versionIdForReport]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !versionIdForReport || !resolvedActiveTab) {
      return undefined;
    }
    const step = resolvedActiveTab;
    fetchStrategyStepReport(strategyName, step, versionIdForReport)
      .then((msg) => {
        if (cancelled) return;
        const rep = msg?.report;
        const slot = rep && typeof rep === 'object' ? rep : null;
        setStepReportSlots((prev) => ({ ...prev, [step]: slot }));
      })
      .catch(() => {
        if (cancelled) return;
        setStepReportSlots((prev) => ({ ...prev, [step]: null }));
      });
    return () => {
      cancelled = true;
    };
  }, [strategyName, versionIdForReport, resolvedActiveTab]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !versionIdForReport || resolvedActiveTab !== 'enum') {
      setEnumRefStatus('idle');
      setEnumRefRows([]);
      return undefined;
    }
    setEnumRefStatus('loading');
    fetchStrategyStepReportRef(strategyName, 'enum', versionIdForReport).then((msg) => {
      if (cancelled) return;
      const raw = msg?.stock_ref;
      const available = msg?.stock_ref_available !== false;
      if (
        available
        && raw
        && typeof raw === 'object'
        && Object.keys(raw).length > 0
      ) {
        const mapped = sortMappedEnumRows(
          mapStockRefToRows(raw),
          ENUM_REF_DEFAULT_SORT.sortBy,
          ENUM_REF_DEFAULT_SORT.order,
        );
        setEnumRefRows(mapped);
        setEnumRefStatus('ok');
        return;
      }
      setEnumRefRows([]);
      setEnumRefStatus('missing');
    });
    return () => {
      cancelled = true;
    };
  }, [resolvedActiveTab, strategyName, versionIdForReport]);

  return {
    reportStocks,
    enumRefStatus,
    enumRefRows,
    availableTabs,
    resolvedActiveTab,
    stepReportSlots,
  };
}
