import { useEffect, useState } from 'react';
import {
  fetchStrategyReportCompare,
  fetchStrategyVersionDetail,
} from '../../../../../api/apis/strategyApi';
import { REPORT_COMPARE_MORE_MENU_VALUE } from '../constants/strategyReportConstants';

/**
 * 「对比结果」弹窗：对比版本选择、报告对比 API、当前/对比快照 settings 加载。
 */
export function useStrategyReportCompareDialog({
  strategyName,
  runId,
  anchorVersionId,
  resolvedActiveTab,
  showReportCompare,
}) {
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [compareDialogSubTab, setCompareDialogSubTab] = useState('report');
  const [reportCompareMoreOpen, setReportCompareMoreOpen] = useState(false);
  const [baseSettingsPayload, setBaseSettingsPayload] = useState({
    loading: false,
    error: '',
    settings: null,
  });
  const [compareWorkbenchSnapshot, setCompareWorkbenchSnapshot] = useState({
    loading: false,
    error: '',
    detail: null,
  });
  const [compareVersion, setCompareVersion] = useState('');
  const [comparePayload, setComparePayload] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');

  useEffect(() => {
    if (!showReportCompare && compareDialogOpen) setCompareDialogOpen(false);
  }, [showReportCompare, compareDialogOpen]);

  useEffect(() => {
    let cancelled = false;
    if (!compareDialogOpen || !strategyName || !runId || !resolvedActiveTab || !compareVersion) {
      setComparePayload(null);
      setCompareError('');
      setCompareLoading(false);
      return undefined;
    }
    const loadCompare = async () => {
      try {
        setCompareLoading(true);
        setCompareError('');
        const data = await fetchStrategyReportCompare(
          strategyName,
          runId,
          compareVersion,
          resolvedActiveTab,
        );
        if (cancelled) return;
        setComparePayload(data || null);
      } catch (err) {
        if (cancelled) return;
        setCompareError(err?.message || '读取对比报告失败');
        setComparePayload(null);
      } finally {
        if (!cancelled) setCompareLoading(false);
      }
    };
    loadCompare();
    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareVersion, resolvedActiveTab, runId, strategyName]);

  useEffect(() => {
    if (!compareDialogOpen) {
      setCompareDialogSubTab('report');
      setReportCompareMoreOpen(false);
    }
  }, [compareDialogOpen]);

  useEffect(() => {
    if (!compareDialogOpen || compareDialogSubTab !== 'settings' || !strategyName) {
      setBaseSettingsPayload({ loading: false, error: '', settings: null });
      return undefined;
    }
    let cancelled = false;
    const curId = String(anchorVersionId || '').trim();

    if (!curId) {
      setBaseSettingsPayload({ loading: false, error: '', settings: null });
    } else {
      setBaseSettingsPayload((prev) => ({ ...prev, loading: true, error: '' }));
      fetchStrategyVersionDetail(strategyName, curId)
        .then((res) => {
          if (cancelled) return;
          setBaseSettingsPayload({
            loading: false,
            error: '',
            settings: res?.settings ?? null,
          });
        })
        .catch((err) => {
          if (cancelled) return;
          setBaseSettingsPayload({
            loading: false,
            error: err?.message || '读取当前快照设置失败',
            settings: null,
          });
        });
    }

    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareDialogSubTab, strategyName, anchorVersionId]);

  useEffect(() => {
    if (!compareDialogOpen || !strategyName || !String(compareVersion || '').trim()) {
      setCompareWorkbenchSnapshot({ loading: false, error: '', detail: null });
      return undefined;
    }
    let cancelled = false;
    const vid = String(compareVersion).trim();
    setCompareWorkbenchSnapshot((prev) => ({ ...prev, loading: true, error: '' }));
    fetchStrategyVersionDetail(strategyName, vid)
      .then((detail) => {
        if (cancelled) return;
        setCompareWorkbenchSnapshot({ loading: false, error: '', detail });
      })
      .catch((err) => {
        if (cancelled) return;
        setCompareWorkbenchSnapshot({
          loading: false,
          error: err?.message || '读取对比快照失败',
          detail: null,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareVersion, strategyName]);

  const handleReportCompareSelectChange = (event) => {
    const value = event.target.value;
    const proceed = () => {
      if (value === REPORT_COMPARE_MORE_MENU_VALUE) {
        setReportCompareMoreOpen(true);
        return;
      }
      setCompareVersion(value);
    };
    window.setTimeout(proceed, 0);
  };

  const compareResultReport = compareWorkbenchSnapshot.detail?.result_report
    && typeof compareWorkbenchSnapshot.detail.result_report === 'object'
    ? compareWorkbenchSnapshot.detail.result_report
    : null;

  const compareSideReportBusy = Boolean(
    compareVersion && (compareLoading || compareWorkbenchSnapshot.loading),
  );

  return {
    compareDialogOpen,
    setCompareDialogOpen,
    compareDialogSubTab,
    setCompareDialogSubTab,
    reportCompareMoreOpen,
    setReportCompareMoreOpen,
    baseSettingsPayload,
    compareWorkbenchSnapshot,
    compareVersion,
    setCompareVersion,
    comparePayload,
    compareLoading,
    compareError,
    handleReportCompareSelectChange,
    compareResultReport,
    compareSideReportBusy,
  };
}
