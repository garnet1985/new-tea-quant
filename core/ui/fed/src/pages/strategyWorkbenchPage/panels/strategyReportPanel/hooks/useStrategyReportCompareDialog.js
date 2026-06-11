import { useEffect, useState } from 'react';
import { fetchStrategyVersionDetail } from '../../../../../api/apis/strategyApi';
import { buildWorkbenchSnapshotFromVersionDetail } from '../../../workbenchSnapshot';
import { REPORT_COMPARE_MORE_MENU_VALUE } from '../constants/strategyReportConstants';

/**
 * 「对比结果」弹窗：对比版本 V2-08 快照、settings diff。
 */
export function useStrategyReportCompareDialog({
  strategyName,
  workbenchSnapshot,
  resolvedActiveTab,
  showReportCompare,
}) {
  const baseVersionId = String(workbenchSnapshot?.versionId || '').trim();
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [compareDialogSubTab, setCompareDialogSubTab] = useState('report');
  const [reportCompareMoreOpen, setReportCompareMoreOpen] = useState(false);
  const [compareVersion, setCompareVersion] = useState('');
  const [compareError, setCompareError] = useState('');
  const [compareSnapshot, setCompareSnapshot] = useState(null);
  const [compareSnapshotLoading, setCompareSnapshotLoading] = useState(false);

  useEffect(() => {
    if (!showReportCompare && compareDialogOpen) setCompareDialogOpen(false);
  }, [showReportCompare, compareDialogOpen]);

  useEffect(() => {
    let cancelled = false;
    const cmpVid = String(compareVersion || '').trim();
    if (!compareDialogOpen || !strategyName || !cmpVid) {
      setCompareSnapshot(null);
      setCompareSnapshotLoading(false);
      setCompareError('');
      return undefined;
    }
    setCompareSnapshotLoading(true);
    setCompareError('');
    fetchStrategyVersionDetail(strategyName, cmpVid)
      .then((detail) => {
        if (cancelled) return;
        setCompareSnapshot(buildWorkbenchSnapshotFromVersionDetail(detail));
      })
      .catch((err) => {
        if (cancelled) return;
        setCompareSnapshot(null);
        setCompareError(err?.message || '读取对比快照失败');
      })
      .finally(() => {
        if (!cancelled) setCompareSnapshotLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareVersion, strategyName]);

  useEffect(() => {
    if (!compareDialogOpen) {
      setCompareDialogSubTab('report');
      setReportCompareMoreOpen(false);
    }
  }, [compareDialogOpen]);

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

  const compareSideReportBusy = Boolean(compareVersion && compareSnapshotLoading);

  const baseSettings = workbenchSnapshot?.settings ?? null;
  const compareSettings = compareSnapshot?.settings ?? null;

  return {
    compareDialogOpen,
    setCompareDialogOpen,
    compareDialogSubTab,
    setCompareDialogSubTab,
    reportCompareMoreOpen,
    setReportCompareMoreOpen,
    baseVersionId,
    compareVersion,
    setCompareVersion,
    compareError,
    handleReportCompareSelectChange,
    compareSnapshot,
    compareSideReportBusy,
    baseSettings,
    compareSettings,
    compareSettingsLoading: compareSideReportBusy,
  };
}
