/**
 * 与 ``EXECUTE_SETTINGS_FIELDS`` 对齐：胶囊「设置已变更」只比这些功能块。
 * enumerator / price_simulator / meta / analysis 不参与。
 *
 * 比较前：migrate → 白名单切片 → 去草稿/空对象 → 填 Python ``to_usable`` 默认值。
 * 默认值快照 = ``StrategySettings.extract_execute_settings({})``，与哈希同一套投影。
 */

import { migrateLegacyStrategySettings } from '../../../utils/stripLegacyStrategySettings';

export const EXECUTE_SETTINGS_FIELDS = [
  'core',
  'data',
  'goal',
  'sampling',
  'fees',
  'simulation',
  'portfolio',
  'market_profile',
];

const EXECUTE_NESTED_DROP_KEYS = new Set(['force_exit_when_draft']);

/** 与 ``extract_execute_settings({})`` 对齐；缺 key 视同默认值。 */
export const EXECUTE_SETTINGS_DEFAULTS = {
  data: {
    base: {
      data_key: 'stock.kline.daily',
      params: { adjust: 'qfq' },
    },
    min_required_records: 100,
    required: [],
  },
  portfolio: {
    allocation: {
      kelly_fraction: 0.5,
      lots_per_trade: 1,
      max_portfolio_size: 10,
      max_weight_per_stock: 0.3,
      mode: 'equal_capital',
      skip_trade_when_insufficient: false,
    },
    initial_capital: 1000000,
    output: {
      save_equity_curve: true,
      save_trades: true,
    },
  },
  simulation: {
    assumption: {
      target_check_order: [
        'check_stop_loss',
        'check_take_profit',
        'check_expiration',
      ],
      template: 'none',
      tradability: {
        delisted_exit_price: 'last_tradable_close',
        edges: {
          allow_enter_at_limit_up: false,
          allow_exit_at_limit_down: false,
          no_next_tick: 'skip_trade',
        },
        enter_price: 'touch',
        exit_price: 'close',
        liquidity: {
          max_participation_rate: 0.1,
          participation_on_exceed: 'clip',
        },
        monitor_price: 'close',
        slippage: {
          enter_bps: 0.0,
          exit_bps: 0.0,
        },
      },
    },
    execution: {
      end_date: '',
      mode: 'entity_based',
      start_date: '',
    },
    risk_control: {
      force_exit_when: [],
      pending_enter: {
        abort_enter_when: [],
        max_entry_drift: null,
        max_wait_open_days: 5,
      },
      skip_enter_when: [],
    },
  },
};

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
  EXECUTE_SETTINGS_FIELDS.forEach((key) => {
    if (src[key] !== undefined) {
      out[key] = src[key];
    }
  });
  return out;
}

/** 去掉空对象，避免 freeze / 编辑器占位误报变更。 */
export function pruneEmptyObjects(value) {
  if (value === null || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map((item) => pruneEmptyObjects(item));
  const out = {};
  Object.keys(value).forEach((key) => {
    if (EXECUTE_NESTED_DROP_KEYS.has(key)) return;
    const next = pruneEmptyObjects(value[key]);
    if (next && typeof next === 'object' && !Array.isArray(next) && Object.keys(next).length === 0) {
      return;
    }
    out[key] = next;
  });
  return out;
}

function cloneJson(value) {
  if (value === undefined) return value;
  return JSON.parse(JSON.stringify(value));
}

/** overlay 覆盖 defaults；缺的 key 保留默认。数组/标量整段替换。 */
export function deepMergeDefaults(defaults, overlay) {
  if (overlay === undefined) return cloneJson(defaults);
  if (overlay === null || typeof overlay !== 'object' || Array.isArray(overlay)) {
    return overlay;
  }
  const base = (defaults && typeof defaults === 'object' && !Array.isArray(defaults))
    ? defaults
    : {};
  const out = { ...base };
  Object.keys(overlay).forEach((key) => {
    out[key] = deepMergeDefaults(base[key], overlay[key]);
  });
  return out;
}

export function fingerprintSignature(settings) {
  const sliced = pruneEmptyObjects(fingerprintSlice(
    migrateLegacyStrategySettings(settings || {}),
  ));
  return stableStringify(pruneEmptyObjects(
    deepMergeDefaults(EXECUTE_SETTINGS_DEFAULTS, sliced),
  ));
}

export function isFingerprintEqual(left, right) {
  return fingerprintSignature(left) === fingerprintSignature(right);
}
