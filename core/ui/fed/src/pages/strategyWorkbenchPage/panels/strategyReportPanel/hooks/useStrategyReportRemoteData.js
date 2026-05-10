import { useEffect, useMemo, useState } from 'react';
import { fetchStrategyReportStocks, fetchStrategyReports, fetchStrategyStepReportRef } from '../../../../../api/apis/strategyApi';
import { STEP_TABS } from '../constants/strategyReportConstants';
import {
  ENUM_REF_DEFAULT_SORT,
  mapStockRefToRows,
  sortMappedEnumRows,
} from '../lib/strategyReportEnumRef';

/**
 * 远程报告摘要、逐股样本、枚举 report_ref；并在 hook 内推导 ``availableTabs`` / ``resolvedActiveTab``，避免与父组件循环依赖。
 */
export function useStrategyReportRemoteData({
  strategyName,
  runId,
  anchorVersionId,
  activeTab,
  executionState,
}) {
  const [remoteReports, setRemoteReports] = useState({ reports: {}, availableTabs: [] });
  const [reportStocks, setReportStocks] = useState({ enum: [], price: [], capital: [] });
  const [reportError, setReportError] = useState('');
  const [enumRefStatus, setEnumRefStatus] = useState('idle');
  const [enumRefRows, setEnumRefRows] = useState([]);

  const availableTabs = useMemo(() => {
    const remoteTabs = Array.isArray(remoteReports?.availableTabs)
      ? remoteReports.availableTabs
      : [];
    if (remoteTabs.length > 0) {
      return STEP_TABS.filter((tab) => remoteTabs.includes(tab.key));
    }
    const stepStatus = executionState?.stepStatus || {};
    return STEP_TABS.filter((tab) => stepStatus[tab.key] === 'done');
  }, [executionState, remoteReports]);

  const resolvedActiveTab = useMemo(() => {
    if (availableTabs.length === 0) return '';
    if (availableTabs.some((tab) => tab.key === activeTab)) return activeTab;
    return availableTabs[availableTabs.length - 1].key;
  }, [activeTab, availableTabs]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !anchorVersionId || resolvedActiveTab !== 'enum') {
      setEnumRefStatus('idle');
      setEnumRefRows([]);
      return undefined;
    }
    setEnumRefStatus('loading');
    fetchStrategyStepReportRef(strategyName, 'enum', anchorVersionId).then((msg) => {
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
  }, [anchorVersionId, resolvedActiveTab, strategyName]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !runId) {
      setRemoteReports({ reports: {}, availableTabs: [] });
      setReportStocks({ enum: [], price: [], capital: [] });
      setReportError('');
      return undefined;
    }
    const loadReports = async () => {
      try {
        setReportError('');
        const data = await fetchStrategyReports(strategyName, runId);
        if (cancelled) return;
        setRemoteReports({
          reports: data?.reports || {},
          availableTabs: data?.available_tabs || [],
        });
      } catch (err) {
        if (cancelled) return;
        setReportError(err?.message || '读取报告摘要失败');
        setRemoteReports({ reports: {}, availableTabs: [] });
      }
    };
    loadReports();
    return () => {
      cancelled = true;
    };
  }, [runId, strategyName]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !runId || !resolvedActiveTab) return undefined;
    const loadStocks = async () => {
      try {
        const data = await fetchStrategyReportStocks(strategyName, runId, resolvedActiveTab, { limit: 10 });
        if (cancelled) return;
        const rows = Array.isArray(data?.rows) ? data.rows : [];
        const mapped = rows.map((row, index) => {
          if (resolvedActiveTab === 'enum') {
            return {
              id: `${row.stock_id}-${index}`,
              stockCode: row.stock_id,
              stockName: row.stock_name,
              opportunities: Number(row.opportunities || 0),
              completionRate: Number(row.completion_rate || 0),
              triggerSpanDays: Number(row.trigger_span_days || 0),
            };
          }
          if (resolvedActiveTab === 'price') {
            return {
              id: `${row.stock_id}-${index}`,
              stockCode: row.stock_id,
              stockName: row.stock_name,
              winRate: Number(row.win_rate || 0),
              roi: Number(row.roi || 0),
              holdDays: Number(row.hold_days || 0),
            };
          }
          return {
            id: `${row.stock_id}-${index}`,
            stockCode: row.stock_id,
            stockName: row.stock_name,
            tradeCount: Number(row.trade_count || 0),
            pnl: Number(row.pnl || 0),
            winRate: Number(row.win_rate || 0),
          };
        });
        setReportStocks((prev) => ({ ...prev, [resolvedActiveTab]: mapped }));
      } catch (err) {
        if (cancelled) return;
        setReportStocks((prev) => ({ ...prev, [resolvedActiveTab]: [] }));
      }
    };
    loadStocks();
    return () => {
      cancelled = true;
    };
  }, [resolvedActiveTab, runId, strategyName]);

  return {
    remoteReports,
    reportStocks,
    reportError,
    enumRefStatus,
    enumRefRows,
    availableTabs,
    resolvedActiveTab,
  };
}
