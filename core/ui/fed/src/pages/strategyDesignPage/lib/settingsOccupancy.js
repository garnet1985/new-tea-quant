import { stripLegacyStrategySettingsForRun } from '../../../utils/stripLegacyStrategySettings';
import { stableStringify } from './strategySettingsFingerprint';

export const SETTINGS_CONFLICT_CODE = 'settings_conflict';

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value ?? {}));
}

/** Persist / 脏检查用的可写回形态（与 Run 提交同一套 strip）。 */
export function persistComparable(settings) {
  return stripLegacyStrategySettingsForRun(
    cloneJson(settings && typeof settings === 'object' ? settings : {}),
  );
}

export function isDraftDirty(draft, loaded) {
  return stableStringify(persistComparable(draft))
    !== stableStringify(persistComparable(loaded));
}

export function isSettingsConflictError(err) {
  return String(err?.code || err?.payload?.code || '') === SETTINGS_CONFLICT_CODE;
}

export function occupancyFromPayload(payload) {
  const src = payload && typeof payload === 'object' ? payload : {};
  return {
    settings_rev: String(src.settings_rev || ''),
    disk_settings: src.disk_settings && typeof src.disk_settings === 'object'
      ? src.disk_settings
      : {},
    execute_settings: src.execute_settings && typeof src.execute_settings === 'object'
      ? src.execute_settings
      : {},
  };
}

export function occupancyFromError(err) {
  return occupancyFromPayload(err?.payload);
}
