import { useEffect, useState } from 'react';
import {
  fetchStrategyStepReport,
  fetchStrategyVersionDetail,
} from '../../../../../api/apis/strategyApi';
import { REPORT_COMPARE_MORE_MENU_VALUE } from '../constants/strategyReportConstants';

/**
 * 「对比结果」弹窗：对比版本选择、V2-07 对比侧 report、settings 快照 diff。
 */
export function useStrategyReportCompareDialog({
  strategyName,
  reportVersionId,
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
  const [compareError, setCompareError] = useState('');
  const [compareStepReport, setCompareStepReport] = useState(null);
  const [compareStepReportLoading, setCompareStepReportLoading] = useState(false);

  useEffect(() => {
    if (!showReportCompare && compareDialogOpen) setCompareDialogOpen(false);
  }, [showReportCompare, compareDialogOpen]);

  useEffect(() => {
    let cancelled = false;
    const cmpVid = String(compareVersion || '').trim();
    if (!compareDialogOpen || !strategyName || !resolvedActiveTab || !cmpVid) {
      setCompareStepReport(null);
      setCompareStepReportLoading(false);
      setCompareError('');
      return undefined;
    }
    setCompareStepReportLoading(true);
    setCompareError('');
    fetchStrategyStepReport(strategyName, resolvedActiveTab, cmpVid)
      .then((msg) => {
        if (cancelled) return;
        const rep = msg?.report;
        setCompareStepReport(rep && typeof rep === 'object' ? rep : null);
      })
      .catch((err) => {
        if (cancelled) return;
        setCompareStepReport(null);
        setCompareError(err?.message || '读取对比报告失败');
      })
      .finally(() => {
        if (!cancelled) setCompareStepReportLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareVersion, resolvedActiveTab, strategyName]);

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
    const curId = String(reportVersionId || '').trim();

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
  }, [compareDialogOpen, compareDialogSubTab, strategyName, reportVersionId]);

  useEffect(() => {
    if (
      !compareDialogOpen
      || compareDialogSubTab !== 'settings'
      || !strategyName
      || !String(compareVersion || '').trim()
    ) {
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
  }, [compareDialogOpen, compareDialogSubTab, compareVersion, strategyName]);

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

  const compareSideReportBusy = Boolean(compareVersion && compareStepReportLoading);

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
    compareError,
    handleReportCompareSelectChange,
    compareStepReport,
    compareSideReportBusy,
  };
}
