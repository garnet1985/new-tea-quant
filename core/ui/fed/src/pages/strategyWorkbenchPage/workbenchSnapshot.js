/**
 * 工作台快照 DTO（V2-01 / V2-08 同形）：右侧执行/报告面板的单一数据源。
 */

/** @returns {{ versionId: string, step_status: object|null, result_report: object|null, execution_panel: object|null, settings: object|null }} */
export function emptyWorkbenchSnapshot() {
  return {
    versionId: '',
    step_status: null,
    result_report: null,
    execution_panel: null,
    settings: null,
  };
}

/**
 * @param {object|null|undefined} detail V2-08 ``fetchStrategyVersionDetail`` 或 restore 返回的 detail
 */
export function buildWorkbenchSnapshotFromVersionDetail(detail) {
  if (!detail || typeof detail !== 'object') {
    return emptyWorkbenchSnapshot();
  }
  const versionId = typeof detail.version_id === 'string' ? detail.version_id.trim() : '';
  return {
    versionId,
    step_status: detail.step_status ?? null,
    result_report: detail.result_report ?? null,
    execution_panel: detail.execution_panel ?? null,
    settings: detail.settings ?? null,
  };
}

/**
 * @param {object|null|undefined} res V2-01 ``fetchStrategySettings`` 响应
 */
export function buildWorkbenchSnapshotFromSettingsResponse(res) {
  if (!res || typeof res !== 'object') {
    return emptyWorkbenchSnapshot();
  }
  const versionId = typeof res.workbench_version_id === 'string'
    ? res.workbench_version_id.trim()
    : '';
  return {
    versionId,
    step_status: res.step_status ?? null,
    result_report: res.result_report ?? null,
    execution_panel: res.execution_panel ?? null,
    settings: res.settings ?? null,
  };
}
