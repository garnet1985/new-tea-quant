/**
 * 从 Run 提交 payload 中移除已迁出 strategy settings 的 dispatch / performance 字段。
 * 并对旧 key / 扁平 simulation / goal 字段做迁移，对齐新 strategy 模块 settings 形状。
 */

const ENUMERATOR_DISPATCH_KEYS = [
  'max_workers',
  'max_parallel_jobs_cap',
  'is_verbose',
  'memory_budget_mb',
  'memory_floor_mb',
  'main_process_reserve_mb',
  'warmup_batch_size',
  'min_batch_size',
  'max_batch_size',
  'monitor_interval',
  'entities_per_job',
  'entities_per_job_min',
  'entities_per_job_max',
  'dispatch_probe',
  'dispatch_probe_entities',
  'dispatch_probe_safety_factor',
  'mb_per_entity_staged',
  'worker_memory_fraction',
  'prefetch_ahead',
  'max_test_versions',
];

const PRICE_SIMULATOR_DISPATCH_KEYS = [
  'max_workers',
  'max_parallel_jobs_cap',
  'entities_per_job',
  'dispatch_probe',
  'dispatch_probe_entities',
  'dispatch_probe_safety_factor',
  'sec_per_entity_staged',
  'sec_per_job_overhead_staged',
  'force_main_process',
  'start_date',
  'end_date',
  'fees',
];

const EXECUTION_MODE_MAP = {
  entity_timeline: 'entity_based',
  calendar_slice: 'slice_based',
  entity_based: 'entity_based',
  slice_based: 'slice_based',
};

function stripKeysFromBlock(block, keys) {
  if (!block || typeof block !== 'object') return block;
  const out = { ...block };
  keys.forEach((key) => {
    delete out[key];
  });
  return out;
}

function ensureDict(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? { ...value } : {};
}

function migrateSimulationBlock(simulation) {
  const src = ensureDict(simulation);
  const alreadyNested = src.execution || src.assumption || src.risk_control;
  const execution = ensureDict(src.execution);
  const assumption = ensureDict(src.assumption);
  const riskControl = ensureDict(src.risk_control);
  const tradability = ensureDict(assumption.tradability);
  const edges = ensureDict(tradability.edges);
  const slippage = ensureDict(tradability.slippage);
  const liquidity = ensureDict(tradability.liquidity);

  // Flat → nested dates / mode
  if (src.start_date && !execution.start_date) execution.start_date = src.start_date;
  if (src.end_date && !execution.end_date) execution.end_date = src.end_date;
  const rawMode = execution.mode || src.execution_mode;
  if (rawMode) {
    execution.mode = EXECUTION_MODE_MAP[String(rawMode)] || String(rawMode);
  }
  if (Array.isArray(src.execute_steps) && src.execute_steps.length > 0 && !execution.steps) {
    execution.steps = [...src.execute_steps];
  }

  // Flat template / tradability → assumption
  if (src.template && !assumption.template) {
    assumption.template = src.template;
  }
  if (src.monitor_price_model && !tradability.monitor_price) {
    tradability.monitor_price = src.monitor_price_model === 'extreme' ? 'close' : src.monitor_price_model;
  }
  if (src.buy_price_model && !tradability.enter_price) {
    const buy = src.buy_price_model;
    tradability.enter_price = buy === 'extreme' ? 'touch' : buy;
  }
  if (src.sell_price_model && !tradability.exit_price) {
    const sell = src.sell_price_model;
    tradability.exit_price = sell === 'extreme' ? 'close' : sell;
  }
  if (src.slippage && typeof src.slippage === 'object') {
    if (src.slippage.buy_bps !== undefined && slippage.enter_bps === undefined) {
      slippage.enter_bps = src.slippage.buy_bps;
    }
    if (src.slippage.sell_bps !== undefined && slippage.exit_bps === undefined) {
      slippage.exit_bps = src.slippage.sell_bps;
    }
    if (src.slippage.enter_bps !== undefined && slippage.enter_bps === undefined) {
      slippage.enter_bps = src.slippage.enter_bps;
    }
    if (src.slippage.exit_bps !== undefined && slippage.exit_bps === undefined) {
      slippage.exit_bps = src.slippage.exit_bps;
    }
  }
  if (src.edges && typeof src.edges === 'object') {
    if (src.edges.no_next_bar && !edges.no_next_tick) {
      edges.no_next_tick = src.edges.no_next_bar === 'unfinished'
        ? 'skip_trade'
        : src.edges.no_next_bar;
    }
    if (src.edges.no_next_tick && !edges.no_next_tick) {
      edges.no_next_tick = src.edges.no_next_tick;
    }
    if (src.edges.allow_buy_at_limit_up !== undefined && edges.allow_enter_at_limit_up === undefined) {
      edges.allow_enter_at_limit_up = src.edges.allow_buy_at_limit_up;
    }
    if (src.edges.allow_sell_at_limit_down !== undefined && edges.allow_exit_at_limit_down === undefined) {
      edges.allow_exit_at_limit_down = src.edges.allow_sell_at_limit_down;
    }
    if (src.edges.allow_enter_at_limit_up !== undefined && edges.allow_enter_at_limit_up === undefined) {
      edges.allow_enter_at_limit_up = src.edges.allow_enter_at_limit_up;
    }
    if (src.edges.allow_exit_at_limit_down !== undefined && edges.allow_exit_at_limit_down === undefined) {
      edges.allow_exit_at_limit_down = src.edges.allow_exit_at_limit_down;
    }
  }
  if (src.liquidity && typeof src.liquidity === 'object') {
    Object.keys(src.liquidity).forEach((key) => {
      if (liquidity[key] === undefined) liquidity[key] = src.liquidity[key];
    });
  }
  if (src.delisted_exit_price && !tradability.delisted_exit_price) {
    tradability.delisted_exit_price = src.delisted_exit_price;
  }

  if (Object.keys(slippage).length > 0) tradability.slippage = slippage;
  if (Object.keys(edges).length > 0) tradability.edges = edges;
  if (Object.keys(liquidity).length > 0) tradability.liquidity = liquidity;
  if (Object.keys(tradability).length > 0) assumption.tradability = tradability;

  // Flat skip → risk_control.skip_enter_when
  if (Array.isArray(src.skip_investment_when) && !Array.isArray(riskControl.skip_enter_when)) {
    riskControl.skip_enter_when = [...src.skip_investment_when];
  }
  if (Array.isArray(src.skip_enter_when) && !Array.isArray(riskControl.skip_enter_when)) {
    riskControl.skip_enter_when = [...src.skip_enter_when];
  }

  // extreme_same_bar_order → target_check_order (best-effort)
  if (!assumption.target_check_order && src.extreme_same_bar_order === 'take_profit_first') {
    assumption.target_check_order = [
      'check_take_profit',
      'check_stop_loss',
      'check_expiration',
    ];
  }

  const out = {};
  if (Object.keys(execution).length > 0) out.execution = execution;
  if (Object.keys(assumption).length > 0) out.assumption = assumption;
  if (Object.keys(riskControl).length > 0) out.risk_control = riskControl;
  if (src.retention && typeof src.retention === 'object') {
    out.retention = { ...src.retention };
  }

  // Preserve unknown nested keys when already nested
  if (alreadyNested) {
    Object.keys(src).forEach((key) => {
      if (out[key] === undefined && !['start_date', 'end_date', 'execution_mode',
        'template', 'monitor_price_model', 'buy_price_model', 'sell_price_model',
        'slippage', 'edges', 'liquidity', 'skip_investment_when', 'skip_enter_when',
        'extreme_same_bar_order', 'extreme_same_bar_random_seed', 'execute_steps',
        'delisted_exit_price'].includes(key)) {
        out[key] = src[key];
      }
    });
  }
  return out;
}

function migrateGoalBlock(goal, riskControl) {
  const next = ensureDict(goal);
  const expiration = ensureDict(next.expiration);
  if (expiration.mode == null && expiration.is_trading_days !== undefined) {
    expiration.mode = expiration.is_trading_days === false ? 'natural_day' : 'trading_day';
  }
  delete expiration.is_trading_days;
  if (Object.keys(expiration).length > 0) next.expiration = expiration;
  else delete next.expiration;

  ['stop_loss', 'take_profit'].forEach((section) => {
    const block = next[section];
    if (!block || typeof block !== 'object' || !Array.isArray(block.stages)) return;
    next[section] = {
      ...block,
      stages: block.stages.map((stage) => {
        if (!stage || typeof stage !== 'object') return stage;
        const row = { ...stage };
        if (row.exit_ratio === undefined && row.sell_ratio !== undefined) {
          row.exit_ratio = row.sell_ratio;
        }
        delete row.sell_ratio;
        return row;
      }),
    };
  });

  // goal.stock_status_risk_management → simulation.risk_control.force_exit_when
  const raw = next.stock_status_risk_management;
  delete next.stock_status_risk_management;
  if (!Array.isArray(riskControl.force_exit_when) || riskControl.force_exit_when.length === 0) {
    let rules = [];
    if (Array.isArray(raw)) rules = raw;
    else if (raw && typeof raw === 'object' && Array.isArray(raw.rules)) rules = raw.rules;
    if (rules.length > 0) {
      riskControl.force_exit_when = rules.map((rule) => {
        if (!rule || typeof rule !== 'object') return rule;
        const status = String(rule.status || rule.name || '').trim().toLowerCase();
        const payload = { status };
        if (rule.close_invest !== undefined) payload.close_invest = Boolean(rule.close_invest);
        if (rule.exit_ratio !== undefined) payload.exit_ratio = rule.exit_ratio;
        else if (rule.sell_ratio !== undefined) payload.exit_ratio = rule.sell_ratio;
        return payload;
      }).filter((rule) => rule && rule.status);
    }
  }

  return next;
}

/**
 * 工作台草稿 / 提交前：旧 section key → 新结构。
 */
export function migrateLegacyStrategySettings(settings) {
  if (!settings || typeof settings !== 'object') return settings;
  const out = { ...settings };

  if (out.capital_simulator && typeof out.capital_simulator === 'object') {
    if (!out.portfolio || typeof out.portfolio !== 'object') {
      out.portfolio = { ...out.capital_simulator };
    } else {
      out.portfolio = { ...out.capital_simulator, ...out.portfolio };
    }
  }
  delete out.capital_simulator;

  const sampling = out.sampling && typeof out.sampling === 'object' ? { ...out.sampling } : null;
  let simulation = ensureDict(out.simulation);
  if (sampling) {
    if (sampling.start_date && !simulation.start_date && !simulation.execution?.start_date) {
      simulation = { ...simulation, start_date: sampling.start_date };
    }
    if (sampling.end_date && !simulation.end_date && !simulation.execution?.end_date) {
      simulation = { ...simulation, end_date: sampling.end_date };
    }
    delete sampling.start_date;
    delete sampling.end_date;
    out.sampling = sampling;
  }

  simulation = migrateSimulationBlock(simulation);
  const riskControl = ensureDict(simulation.risk_control);
  if (out.goal && typeof out.goal === 'object') {
    out.goal = migrateGoalBlock(out.goal, riskControl);
  }
  if (Object.keys(riskControl).length > 0) {
    simulation.risk_control = riskControl;
  }
  out.simulation = simulation;

  return out;
}

export function stripLegacyStrategySettingsForRun(settings) {
  if (!settings || typeof settings !== 'object') return settings;
  const out = migrateLegacyStrategySettings(settings);
  delete out.performance;

  if (out.enumerator) {
    out.enumerator = stripKeysFromBlock(out.enumerator, ENUMERATOR_DISPATCH_KEYS);
  }
  if (out.price_simulator) {
    out.price_simulator = stripKeysFromBlock(out.price_simulator, PRICE_SIMULATOR_DISPATCH_KEYS);
  }
  delete out.scanner;

  return out;
}
