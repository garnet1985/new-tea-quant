/**
 * 与 ``StrategySettings.FINGERPRINT_FIELDS`` 对齐：胶囊「设置已变更」只比这些字段。
 * enumerator / price_simulator / meta / analysis 等不参与 version 指纹，切步填默认值不应误报。
 *
 * 比较前走 ``migrateLegacyStrategySettings``，避免编辑器草稿与 Python freeze
 * 在空嵌套 / 旧 key 形态上误报「设置已变更」。
 */

import { migrateLegacyStrategySettings } from '../../../utils/stripLegacyStrategySettings';

export const STRATEGY_SETTINGS_FINGERPRINT_FIELDS = [
  'core',
  'data',
  'goal',
  'sampling',
  'fees',
  'simulation',
  'portfolio',
  'market_profile',
];

export function stableStringify(value) {
  if (value === undefined) return 'null';
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`;
  }
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

export function fingerprintSlice(settings) {
  const src = settings && typeof settings === 'object' && !Array.isArray(settings)
    ? settings
    : {};
  const out = {};
  STRATEGY_SETTINGS_FINGERPRINT_FIELDS.forEach((key) => {
    if (src[key] !== undefined) {
      out[key] = src[key];
    }
  });
  return out;
}

/** 去掉空对象，避免 freeze / 编辑器在空 slippage 等占位上误报变更。 */
export function pruneEmptyObjects(value) {
  if (value === null || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map((item) => pruneEmptyObjects(item));
  const out = {};
  Object.keys(value).forEach((key) => {
    const next = pruneEmptyObjects(value[key]);
    if (next && typeof next === 'object' && !Array.isArray(next) && Object.keys(next).length === 0) {
      return;
    }
    out[key] = next;
  });
  return out;
}

export function fingerprintSignature(settings) {
  return stableStringify(pruneEmptyObjects(fingerprintSlice(
    migrateLegacyStrategySettings(settings || {}),
  )));
}

export function isFingerprintEqual(left, right) {
  return fingerprintSignature(left) === fingerprintSignature(right);
}
