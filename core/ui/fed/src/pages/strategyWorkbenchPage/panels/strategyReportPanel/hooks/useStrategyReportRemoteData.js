import { useEffect, useMemo, useState } from 'react';
import { fetchStrategyStepReportRef } from '../../../../../api/apis/strategyApi';
import { STEP_TABS } from '../constants/strategyReportConstants';
import {
  ENUM_REF_DEFAULT_SORT,
  mapStockRefToRows,
  sortMappedEnumRows,
} from '../lib/strategyReportEnumRef';
import {
  PRICE_REF_DEFAULT_SORT,
  mapPriceStockRefToRows,
  sortMappedPriceRows,
} from '../lib/strategyReportPriceRef';

/**
 * 报告面板远程数据：枚举 ``report_ref``（V2-07b）与可用 Tab 推导。
 * 主面板与对比弹窗读页面注入的 V2-08 ``workbenchSnapshot.result_report``；枚举明细仍用 V2-07b ``report_ref``。
 */
export function useStrategyReportRemoteData({
  strategyName,
  reportVersionId,
  activeTab,
  executionState,
  /** 制定策略等单步视图：固定当前 Tab，不随 availableTabs 回退 */
  lockedTab = '',
}) {
  const versionIdForReport = String(reportVersionId || '').trim();
  const [enumRefStatus, setEnumRefStatus] = useState('idle');
  const [enumRefRows, setEnumRefRows] = useState([]);
  const [priceRefStatus, setPriceRefStatus] = useState('idle');
  const [priceRefRows, setPriceRefRows] = useState([]);

  const availableTabs = useMemo(() => {
    const stepStatus = executionState?.stepStatus || {};
    return STEP_TABS.filter((tab) => stepStatus[tab.key] === 'done');
  }, [executionState]);

  const resolvedActiveTab = useMemo(() => {
    const lt = String(lockedTab || '').trim();
    if (lt && STEP_TABS.some((tab) => tab.key === lt)) return lt;
    if (availableTabs.length === 0) return '';
    if (availableTabs.some((tab) => tab.key === activeTab)) return activeTab;
    return availableTabs[availableTabs.length - 1].key;
  }, [activeTab, availableTabs, lockedTab]);

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

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !versionIdForReport || resolvedActiveTab !== 'price') {
      setPriceRefStatus('idle');
      setPriceRefRows([]);
      return undefined;
    }
    setPriceRefStatus('loading');
    fetchStrategyStepReportRef(strategyName, 'price', versionIdForReport).then((msg) => {
      if (cancelled) return;
      const raw = msg?.stock_ref;
      const available = msg?.stock_ref_available !== false;
      if (
        available
        && raw
        && typeof raw === 'object'
        && Object.keys(raw).length > 0
      ) {
        const mapped = sortMappedPriceRows(
          mapPriceStockRefToRows(raw),
          PRICE_REF_DEFAULT_SORT.sortBy,
          PRICE_REF_DEFAULT_SORT.order,
        );
        setPriceRefRows(mapped);
        setPriceRefStatus('ok');
        return;
      }
      setPriceRefRows([]);
      setPriceRefStatus('missing');
    });
    return () => {
      cancelled = true;
    };
  }, [resolvedActiveTab, strategyName, versionIdForReport]);

  return {
    enumRefStatus,
    enumRefRows,
    priceRefStatus,
    priceRefRows,
    availableTabs,
    resolvedActiveTab,
  };
}
