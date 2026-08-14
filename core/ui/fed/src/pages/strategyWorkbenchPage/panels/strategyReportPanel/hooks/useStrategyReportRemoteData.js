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
import { slotFromResultReport } from '../lib/strategyReportSlotResolve';

/** 槽位产物变更 / 单步跑完时触发 ``report_ref`` 重拉（避免同 version 下逐股表不刷新）。 */
function stockRefRefreshToken(resultReport, tabKey) {
  const slot = slotFromResultReport(resultReport, tabKey);
  if (!slot || typeof slot !== 'object') return '';
  if (tabKey === 'price') {
    const run = slot.output_version_run;
    if (run && typeof run === 'object') {
      const dir = String(run.output_version_dir || '').trim();
      const vid = run.output_version_id;
      if (dir || vid != null) return `${dir}:${vid ?? ''}`;
    }
    if (slot.output_version_id != null) return String(slot.output_version_id);
    return '';
  }
  if (tabKey === 'enum') {
    const dir = String(slot.enumerator_output_dir || '').trim();
    const vid = slot.output_version_id;
    if (dir || vid != null) return `${dir}:${vid ?? ''}`;
    return '';
  }
  return '';
}

/**
 * 报告面板远程数据：枚举 ``report_ref``（V2-07b）与可用 Tab 推导。
 * 主面板与对比弹窗读页面注入的 V2-08 ``workbenchSnapshot.result_report``；枚举明细仍用 V2-07b ``report_ref``。
 */
export function useStrategyReportRemoteData({
  strategyName,
  reportVersionId,
  activeTab,
  executionState,
  resultReport = null,
  reportTabFocusRequest = null,
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

  const enumRefRefreshKey = useMemo(() => {
    const slotToken = stockRefRefreshToken(resultReport, 'enum');
    const focusTick = reportTabFocusRequest?.step === 'enum'
      ? Number(reportTabFocusRequest.tick) || 0
      : 0;
    const stepDone = executionState?.stepStatus?.enum === 'done' ? 1 : 0;
    return `${slotToken}|f${focusTick}|d${stepDone}`;
  }, [executionState?.stepStatus?.enum, reportTabFocusRequest, resultReport]);

  const priceRefRefreshKey = useMemo(() => {
    const slotToken = stockRefRefreshToken(resultReport, 'price');
    const focusTick = reportTabFocusRequest?.step === 'price'
      ? Number(reportTabFocusRequest.tick) || 0
      : 0;
    const stepDone = executionState?.stepStatus?.price === 'done' ? 1 : 0;
    return `${slotToken}|f${focusTick}|d${stepDone}`;
  }, [executionState?.stepStatus?.price, reportTabFocusRequest, resultReport]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !versionIdForReport || resolvedActiveTab !== 'enum') {
      setEnumRefStatus('idle');
      setEnumRefRows([]);
      return undefined;
    }
    setEnumRefStatus('loading');
    fetchStrategyStepReportRef(strategyName, 'enum', versionIdForReport)
      .then((msg) => {
        if (cancelled) return;
        const raw = msg?.stock_ref;
        const available = msg?.stock_ref_available !== false;
        if (available && raw && typeof raw === 'object') {
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
      })
      .catch(() => {
        if (cancelled) return;
        setEnumRefRows([]);
        setEnumRefStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [enumRefRefreshKey, resolvedActiveTab, strategyName, versionIdForReport]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !versionIdForReport || resolvedActiveTab !== 'price') {
      setPriceRefStatus('idle');
      setPriceRefRows([]);
      return undefined;
    }
    setPriceRefStatus('loading');
    fetchStrategyStepReportRef(strategyName, 'price', versionIdForReport)
      .then((msg) => {
        if (cancelled) return;
        const raw = msg?.stock_ref;
        const available = msg?.stock_ref_available !== false;
        if (available && raw && typeof raw === 'object') {
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
      })
      .catch(() => {
        if (cancelled) return;
        setPriceRefRows([]);
        setPriceRefStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [priceRefRefreshKey, resolvedActiveTab, strategyName, versionIdForReport]);

  return {
    enumRefStatus,
    enumRefRows,
    priceRefStatus,
    priceRefRows,
    availableTabs,
    resolvedActiveTab,
  };
}
