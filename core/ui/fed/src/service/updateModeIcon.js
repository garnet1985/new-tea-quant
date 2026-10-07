/** 更新方式 / renew type 对应 ``NtqIcon`` name（数据源与 Tag 共用）。 */
export function getUpdateModeIcon(mode) {
  const key = String(mode || '').trim().toLowerCase();
  if (key === 'refresh') return 'refresh';
  if (key === 'incremental') return 'add';
  if (key === 'rolling') return 'webhook';
  return 'info';
}
