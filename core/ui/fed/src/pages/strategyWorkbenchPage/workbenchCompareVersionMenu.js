import { useMemo, useCallback } from 'react';

/** 与执行面板「最近版本」下拉一致：至多保留条数 */
export const WORKBENCH_RECENT_COMPARE_VERSION_LIMIT = 5;

export function normalizeRecentCompareVersionIds(rawIds) {
  const raw = Array.isArray(rawIds) ? rawIds : [];
  return raw
    .map((id) => String(id ?? '').trim())
    .filter(Boolean)
    .slice(0, WORKBENCH_RECENT_COMPARE_VERSION_LIMIT);
}

/** 下拉可选对比版本：去掉当前工作台锚定快照，避免与自身对比 */
export function filterCompareDropdownVersionIds(recentIds, currentWorkbenchVersionId) {
  const cur = String(currentWorkbenchVersionId ?? '').trim();
  const recent = Array.isArray(recentIds) ? recentIds : [];
  if (!cur) return recent;
  return recent.filter((id) => id !== cur);
}

/** 未选对比版本时：展示当前工作台快照版本号 +「（当前版本）」 */
export function buildCompareBaselineMenuLabel(currentWorkbenchVersionId) {
  const cur = String(currentWorkbenchVersionId ?? '').trim();
  return cur ? `${cur}（当前版本）` : '—（当前版本）';
}

export function formatCompareSelectDisplayValue(selected, baselineMenuLabel) {
  if (selected === '' || selected == null) return baselineMenuLabel;
  return String(selected);
}

/**
 * 执行面板 / 报告对比弹窗共用的「对比版本」下拉数据。
 * @param {string[]} executionCompareRecentVersionIds 父组件传入的最近 version_id（新→旧）
 * @param {string} currentWorkbenchVersionId 当前锚定工作台快照（``lastCompletedWorkbenchVersionId`` / ``anchorVersionId``）
 */
export function useWorkbenchCompareVersionMenu(
  executionCompareRecentVersionIds,
  currentWorkbenchVersionId,
) {
  const recentCompareIds = useMemo(
    () => normalizeRecentCompareVersionIds(executionCompareRecentVersionIds),
    [executionCompareRecentVersionIds],
  );

  const compareDropdownVersionIds = useMemo(
    () => filterCompareDropdownVersionIds(recentCompareIds, currentWorkbenchVersionId),
    [recentCompareIds, currentWorkbenchVersionId],
  );

  const compareBaselineMenuLabel = useMemo(
    () => buildCompareBaselineMenuLabel(currentWorkbenchVersionId),
    [currentWorkbenchVersionId],
  );

  const renderCompareSelectValue = useCallback(
    (selected) => formatCompareSelectDisplayValue(selected, compareBaselineMenuLabel),
    [compareBaselineMenuLabel],
  );

  return {
    compareDropdownVersionIds,
    compareBaselineMenuLabel,
    renderCompareSelectValue,
  };
}
