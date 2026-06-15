import { buildWorkbenchSnapshotFromVersionDetail } from '../../strategyWorkbenchPage/workbenchSnapshot';

/** 与 BFF ``workbench_latest_ui_flags.has_persisted_snapshot`` 一致：有效快照 id > 0 */
function versionDetailHasPersistedSnapshot(detail) {
  const vid = String(detail?.version_id ?? '').trim();
  if (!vid) return false;
  const n = Number(String(vid).replace(/^v/i, ''));
  return Number.isFinite(n) && n > 0;
}

/**
 * V2-08 单条快照 → 与 ``fetchStrategySettings``（V2-01）对齐的页面状态。
 * @param {object|null|undefined} detail
 * @param {string} strategyName
 * @param {object[]} cachedVersionRows
 */
export function workbenchPageStateFromVersionDetail(detail, strategyName, cachedVersionRows) {
  const wbVer = typeof detail?.version_id === 'string' ? detail.version_id.trim() : '';
  const persisted = versionDetailHasPersistedSnapshot(detail);
  const rows = Array.isArray(cachedVersionRows) ? cachedVersionRows : [];
  const hasOtherVersions = persisted && rows.length >= 2;
  return {
    strategy_name: strategyName,
    settings: detail?.settings || {},
    workbench_version_id: wbVer,
    step_status: detail?.step_status,
    result_report: detail?.result_report ?? null,
    execution_panel: detail?.execution_panel ?? null,
    has_persisted_snapshot: persisted,
    has_other_versions: hasOtherVersions,
  };
}

export { buildWorkbenchSnapshotFromVersionDetail };
