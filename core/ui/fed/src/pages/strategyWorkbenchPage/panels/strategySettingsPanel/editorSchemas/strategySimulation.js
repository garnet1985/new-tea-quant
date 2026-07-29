function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

const TEMPLATE_DEFAULT = 'standard';

const SIMULATION_TEMPLATE_META = {
  standard: {
    label: '标准',
    tooltip: '日常回测默认；touch 进场、常见贴板限制。不知道选什么就用这个。',
  },
  strict: {
    label: '严格',
    tooltip: '更贴近现实；在标准基础上，超参与率时整笔跳过。',
  },
  ideal: {
    label: '理想',
    tooltip: '少市场摩擦的对照组；允许涨跌停成交。',
  },
  extreme: {
    label: '极值压力',
    tooltip: '压力测试；进场用次日开盘等更乐观口径，结果通常更差。',
  },
  none: {
    label: '无预设',
    tooltip: '不使用命名预设，完全按下方显式 tradability 配置。',
  },
  custom: {
    label: '自定义',
    tooltip: '自行配置盯价 / 进出价 / 滑点 / 贴板等；熟悉成交假设时使用。',
  },
};

const DEFAULT_SIMULATION_TEMPLATE_OPTIONS = Object.entries(SIMULATION_TEMPLATE_META).map(
  ([value, meta]) => ({ value, ...meta }),
);

const DEFAULT_SKIP_ENTER_WHEN_OPTIONS = [
  {
    value: 'st',
    label: 'ST',
    tooltip: '触发日处于 ST（含 SST）时，价格/资金回测跳过进场；枚举机会仍保留。',
  },
  {
    value: 'star_st',
    label: '*ST',
    tooltip: '触发日处于 *ST（含 S*ST）时，价格/资金回测跳过进场；枚举机会仍保留。',
  },
];

const KNOWN_STATUS_TAGS = new Set(['st', 'star_st']);

const EXECUTION_MODE_OPTIONS = [
  {
    label: '按实体推进',
    value: 'entity_based',
    tooltip: '每个股票独立时间轴推进（entity_based）。',
  },
  {
    label: '按日历切片',
    value: 'slice_based',
    tooltip: '全市场统一日历轴推进（slice_based）；适合截面依赖场景。',
  },
];

const MONITOR_PRICE_OPTIONS = [
  {
    label: '收盘价',
    value: 'close',
    tooltip: '持仓期间用当日收盘价判断止盈、止损与到期等目标。',
  },
];

const ENTER_PRICE_OPTIONS = [
  {
    label: '触及限价',
    value: 'touch',
    tooltip: '按限价触及语义进场（更贴近实盘）。',
  },
  {
    label: '次日开盘',
    value: 'next_open',
    tooltip: '信号确认后，在下一根 K 线开盘价成交。',
  },
  { label: '开盘价', value: 'open', tooltip: '按信号对应 K 线的开盘价作为理论进场价。' },
  { label: '收盘价', value: 'close', tooltip: '按信号对应 K 线的收盘价作为理论进场价。' },
];

const EXIT_PRICE_OPTIONS = [
  { label: '收盘价', value: 'close', tooltip: '按信号对应 K 线的收盘价作为理论出场价。' },
  { label: '开盘价', value: 'open', tooltip: '按信号对应 K 线的开盘价作为理论出场价。' },
  {
    label: '次日开盘',
    value: 'next_open',
    tooltip: '在下一根 K 线开盘价出场。',
  },
  { label: '最高价', value: 'high', tooltip: '按当日最高价近似出场。' },
  { label: '最低价', value: 'low', tooltip: '按当日最低价近似出场。' },
];

const NO_NEXT_TICK_OPTIONS = [
  {
    label: '用信号日收盘价代替',
    value: 'use_last_close',
    tooltip: '样本最后一根 K 线无法取得次日价时，用当日收盘价完成记账。',
  },
  {
    label: '放弃该笔',
    value: 'skip_trade',
    tooltip: '无法取得下一根 K 线时，跳过该笔进场或出场，不记入成交。',
  },
];

const DELISTED_EXIT_PRICE_OPTIONS = [
  {
    label: '最后可交易收盘',
    value: 'last_tradable_close',
    tooltip: '退市强平时使用最后可交易日收盘价。',
  },
  {
    label: '同 tick 收盘',
    value: 'same_tick_close',
    tooltip: '退市强平时使用触发当日收盘价。',
  },
];

const PARTICIPATION_ON_EXCEED_OPTIONS = [
  {
    label: '缩量成交',
    value: 'clip',
    tooltip: '计划股数超过当日成交量×参与率时，按上限向下取整到最小交易单位后成交。',
  },
  {
    label: '跳过',
    value: 'skip',
    tooltip: '计划股数超过参与率上限时，整笔买卖跳过。',
  },
];

function resolveTemplateOptions(simulationTemplateOptions) {
  const raw = Array.isArray(simulationTemplateOptions) && simulationTemplateOptions.length > 0
    ? simulationTemplateOptions
    : DEFAULT_SIMULATION_TEMPLATE_OPTIONS;
  return raw.map((row) => {
    const meta = SIMULATION_TEMPLATE_META[row.value];
    if (meta) {
      return {
        value: row.value,
        label: meta.label,
        tooltip: row.tooltip || meta.tooltip,
      };
    }
    return {
      value: row.value,
      label: row.label,
      tooltip: row.tooltip || '',
    };
  });
}

export function normalizeSkipEnterWhen(raw) {
  if (!Array.isArray(raw)) return [];
  const out = [];
  raw.forEach((item) => {
    const tag = typeof item === 'object' && item
      ? String(item.status || item.name || '').trim().toLowerCase()
      : String(item || '').trim().toLowerCase();
    if (!KNOWN_STATUS_TAGS.has(tag) || out.includes(tag)) return;
    out.push(tag);
  });
  return out;
}

/** @deprecated 旧名；请用 normalizeSkipEnterWhen */
export const normalizeSkipInvestmentWhen = normalizeSkipEnterWhen;

function resolveSkipEnterWhenOptions(skipEnterWhenOptions) {
  const raw = Array.isArray(skipEnterWhenOptions) && skipEnterWhenOptions.length > 0
    ? skipEnterWhenOptions
    : DEFAULT_SKIP_ENTER_WHEN_OPTIONS;
  return raw.map((row) => ({
    value: row.value,
    label: row.label || row.value,
    tooltip: row.tooltip || '',
  }));
}

function ensureDict(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? { ...value } : {};
}

function mergeTradabilityDefaults(target, defaults) {
  const next = ensureDict(target);
  const src = ensureDict(defaults);
  if (src.slippage && typeof src.slippage === 'object') {
    next.slippage = { ...src.slippage, ...ensureDict(next.slippage) };
  }
  if (src.edges && typeof src.edges === 'object') {
    next.edges = { ...src.edges, ...ensureDict(next.edges) };
  }
  if (src.liquidity && typeof src.liquidity === 'object') {
    next.liquidity = { ...src.liquidity, ...ensureDict(next.liquidity) };
  }
  Object.keys(src).forEach((key) => {
    if (key === 'slippage' || key === 'edges' || key === 'liquidity') return;
    if (next[key] === undefined || next[key] === null || next[key] === '') {
      next[key] = src[key];
    }
  });
  return next;
}

function resolveTemplateDefaults(template, simulationTemplateProfiles) {
  const tpl = template || TEMPLATE_DEFAULT;
  const profiles = simulationTemplateProfiles && typeof simulationTemplateProfiles === 'object'
    ? simulationTemplateProfiles
    : {};
  return profiles[tpl] || profiles.standard || {};
}

/** named 模板只读展示；none/custom 可编辑显式 tradability */
export const isExplicitTradabilityTemplate = (values) => {
  const template = values?.assumption?.template || TEMPLATE_DEFAULT;
  return template === 'custom' || template === 'none';
};

/** @deprecated 兼容旧调用名 */
export const isCustomSimulationTemplate = (values) => {
  if (values?.assumption) return isExplicitTradabilityTemplate(values);
  return (values?.template || TEMPLATE_DEFAULT) === 'custom';
};

function ensureExplicitTradability(tradability) {
  const next = ensureDict(tradability);
  if (!next.monitor_price) next.monitor_price = 'close';
  if (!next.enter_price) next.enter_price = 'touch';
  if (!next.exit_price) next.exit_price = 'close';
  if (!next.slippage || typeof next.slippage !== 'object') {
    next.slippage = { enter_bps: 0, exit_bps: 0 };
  } else {
    if (next.slippage.enter_bps === undefined) next.slippage.enter_bps = 0;
    if (next.slippage.exit_bps === undefined) next.slippage.exit_bps = 0;
  }
  if (!next.edges || typeof next.edges !== 'object') {
    next.edges = {
      no_next_tick: 'skip_trade',
      allow_enter_at_limit_up: false,
      allow_exit_at_limit_down: false,
    };
  } else {
    if (!next.edges.no_next_tick) next.edges.no_next_tick = 'skip_trade';
    if (next.edges.allow_enter_at_limit_up === undefined) {
      next.edges.allow_enter_at_limit_up = false;
    }
    if (next.edges.allow_exit_at_limit_down === undefined) {
      next.edges.allow_exit_at_limit_down = false;
    }
  }
  if (!next.liquidity || typeof next.liquidity !== 'object') {
    next.liquidity = { max_participation_rate: 0.1, participation_on_exceed: 'clip' };
  } else {
    if (next.liquidity.max_participation_rate === undefined
      || next.liquidity.max_participation_rate === null
      || next.liquidity.max_participation_rate === '') {
      next.liquidity.max_participation_rate = 0.1;
    }
    if (!next.liquidity.participation_on_exceed) {
      next.liquidity.participation_on_exceed = 'clip';
    }
  }
  if (!next.delisted_exit_price) next.delisted_exit_price = 'last_tradable_close';
  return next;
}

function normalizeForceExitWhen(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === 'string') {
      const status = String(item).trim().toLowerCase();
      return status ? { status, close_invest: true, exit_ratio: '' } : null;
    }
    if (!item || typeof item !== 'object') return null;
    const status = String(item.status || item.name || '').trim().toLowerCase();
    if (!status) return null;
    const closeInvest = item.close_invest !== false;
    return {
      status,
      close_invest: closeInvest,
      exit_ratio: closeInvest
        ? ''
        : (item.exit_ratio !== undefined ? item.exit_ratio : item.sell_ratio ?? ''),
    };
  }).filter(Boolean);
}

function forceExitDraftFromList(list) {
  const byStatus = {};
  normalizeForceExitWhen(list).forEach((row) => {
    byStatus[row.status] = row;
  });
  return {
    st: byStatus.st || { status: 'st', enabled: false, close_invest: true, exit_ratio: '' },
    star_st: byStatus.star_st || {
      status: 'star_st',
      enabled: false,
      close_invest: true,
      exit_ratio: '',
    },
  };
}

function forceExitListFromDraft(draft) {
  return ['st', 'star_st'].map((status) => {
    const row = draft?.[status];
    if (!row?.enabled) return null;
    if (row.close_invest !== false) return { status, close_invest: true };
    const payload = { status, close_invest: false };
    if (row.exit_ratio !== '' && row.exit_ratio !== undefined && row.exit_ratio !== null) {
      payload.exit_ratio = Number(row.exit_ratio);
    }
    return payload;
  }).filter(Boolean);
}

export function normalizeSimulationSettings(simulation, simulationTemplateProfiles = {}) {
  const src = ensureDict(simulation);
  const execution = ensureDict(src.execution);
  const assumption = ensureDict(src.assumption);
  const riskControl = ensureDict(src.risk_control);

  if (!assumption.template) assumption.template = TEMPLATE_DEFAULT;
  if (!execution.mode) execution.mode = 'entity_based';

  const explicit = assumption.template === 'custom' || assumption.template === 'none';
  if (explicit) {
    assumption.tradability = ensureExplicitTradability(assumption.tradability);
  } else {
    const defaults = resolveTemplateDefaults(assumption.template, simulationTemplateProfiles);
    const defaultTradability = defaults.tradability || defaults;
    assumption.tradability = mergeTradabilityDefaults(
      assumption.tradability,
      defaultTradability,
    );
  }

  riskControl.skip_enter_when = normalizeSkipEnterWhen(
    riskControl.skip_enter_when || src.skip_investment_when,
  );

  const forceDraft = forceExitDraftFromList(riskControl.force_exit_when);
  Object.keys(forceDraft).forEach((status) => {
    const existing = normalizeForceExitWhen(riskControl.force_exit_when)
      .find((row) => row.status === status);
    forceDraft[status] = {
      ...forceDraft[status],
      enabled: Boolean(existing),
      ...(existing || {}),
    };
  });

  return {
    execution,
    assumption,
    risk_control: {
      ...riskControl,
      force_exit_when_draft: forceDraft,
    },
    retention: src.retention && typeof src.retention === 'object' ? { ...src.retention } : undefined,
  };
}

export function resolveSimulationDisplayValue(
  simulation,
  simulationTemplateProfiles = {},
) {
  return normalizeSimulationSettings(simulation, simulationTemplateProfiles);
}

/** named 模板仅持久化 execution + assumption.template(+order) + risk_control；显式模板保留 tradability。 */
export function cleanupSimulationByTemplate(simulation) {
  const next = ensureDict(simulation);
  const execution = ensureDict(next.execution);
  const assumption = ensureDict(next.assumption);
  const riskControl = ensureDict(next.risk_control);

  if (!assumption.template) assumption.template = TEMPLATE_DEFAULT;

  const out = {
    execution: {
      ...(execution.start_date !== undefined && execution.start_date !== null && execution.start_date !== ''
        ? { start_date: execution.start_date }
        : {}),
      ...(execution.end_date !== undefined && execution.end_date !== null && execution.end_date !== ''
        ? { end_date: execution.end_date }
        : {}),
      mode: execution.mode || 'entity_based',
      ...(Array.isArray(execution.steps) && execution.steps.length > 0
        ? { steps: [...execution.steps] }
        : {}),
    },
    assumption: {
      template: assumption.template,
      ...(Array.isArray(assumption.target_check_order) && assumption.target_check_order.length > 0
        ? { target_check_order: [...assumption.target_check_order] }
        : {}),
    },
    risk_control: {
      skip_enter_when: normalizeSkipEnterWhen(riskControl.skip_enter_when),
    },
  };

  const forceList = riskControl.force_exit_when_draft
    ? forceExitListFromDraft(riskControl.force_exit_when_draft)
    : normalizeForceExitWhen(riskControl.force_exit_when).map((row) => {
      if (row.close_invest) return { status: row.status, close_invest: true };
      const payload = { status: row.status, close_invest: false };
      if (row.exit_ratio !== '' && row.exit_ratio !== undefined) {
        payload.exit_ratio = Number(row.exit_ratio);
      }
      return payload;
    });
  if (forceList.length > 0) out.risk_control.force_exit_when = forceList;

  if (riskControl.pending_enter && typeof riskControl.pending_enter === 'object') {
    out.risk_control.pending_enter = { ...riskControl.pending_enter };
  }

  if (isExplicitTradabilityTemplate({ assumption })) {
    out.assumption.tradability = ensureExplicitTradability(assumption.tradability);
  }

  if (next.retention && typeof next.retention === 'object') {
    out.retention = { ...next.retention };
  }
  return out;
}

export function buildStrategySimulationSchema(
  simulationTemplateOptions = DEFAULT_SIMULATION_TEMPLATE_OPTIONS,
  skipEnterWhenOptions = DEFAULT_SKIP_ENTER_WHEN_OPTIONS,
) {
  const templateOptions = resolveTemplateOptions(simulationTemplateOptions);
  const skipOptions = resolveSkipEnterWhenOptions(skipEnterWhenOptions);
  const readonlyUnlessExplicit = ({ values }) => !isExplicitTradabilityTemplate(values);

  return {
    name: 'strategySimulation',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'simulation.dateRange',
        label: '回测时间窗',
        tooltip: 'enum / price / portfolio 共用的行情区间（YYYYMMDD）。开始或结束留空表示由系统按 data.json 边界推断。',
        type: 'dateRange',
        layout: 'vertical',
        startName: 'execution.start_date',
        endName: 'execution.end_date',
        startLabel: '开始日期',
        endLabel: '结束日期',
      },
      {
        name: 'execution.mode',
        type: 'select',
        label: '执行模式',
        tooltip: 'entity_based：逐实体推进；slice_based：统一日历切片。',
        options: EXECUTION_MODE_OPTIONS,
      },
      {
        name: 'assumption.template',
        type: 'select',
        label: '成交假设模板',
        tooltip: '快捷选择 assumption.tradability；除「自定义 / 无预设」外，下方参数只读展示模板默认值。',
        options: templateOptions,
      },
      {
        name: 'assumption.tradability.monitor_price',
        type: 'select',
        label: '盯盘价',
        tooltip: '持仓期间用于止盈、止损、到期等目标比较的每日价格口径。',
        options: MONITOR_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.enter_price',
        type: 'select',
        label: '进场价',
        tooltip: '执行进场时，从 K 线按何种价格语义取理论成交价。',
        options: ENTER_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.exit_price',
        type: 'select',
        label: '出场价',
        tooltip: '执行出场时，从 K 线按何种价格语义取理论成交价。',
        options: EXIT_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.slippage.enter_bps',
        type: 'number',
        label: '进场滑点',
        tooltip: '在理论进场价上叠加滑点，单位为基点（bps）。',
        parse: parseNumber,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.slippage.exit_bps',
        type: 'number',
        label: '出场滑点',
        tooltip: '在理论出场价上叠加滑点，单位为基点（bps）。',
        parse: parseNumber,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.edges.no_next_tick',
        type: 'select',
        label: '样本末日无下一 tick',
        tooltip: '采样区间最后一根 K 线无法取得「次日」价格时的处理方式。',
        options: NO_NEXT_TICK_OPTIONS,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.edges.allow_enter_at_limit_up',
        type: 'switch',
        label: '涨停日允许进场',
        tooltip: '关闭后，遇到涨停且无法按规则进场时将跳过该笔。',
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.edges.allow_exit_at_limit_down',
        type: 'switch',
        label: '跌停日允许出场',
        tooltip: '关闭后，遇到跌停且无法按规则出场时将跳过该笔。',
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.liquidity.max_participation_rate',
        type: 'number',
        label: '最大参与率',
        tooltip: '单笔成交不超过当日 tick 成交量（股）的该比例；默认 0.1 即 10%。',
        parse: parseNumber,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.liquidity.participation_on_exceed',
        type: 'select',
        label: '超参与率时',
        tooltip: '计划股数超过当日成交量×参与率时的处理方式。',
        options: PARTICIPATION_ON_EXCEED_OPTIONS,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'assumption.tradability.delisted_exit_price',
        type: 'select',
        label: '退市强平定价',
        tooltip: '退市强平时使用哪根 tick 定价（是否强平由风控/引擎决定）。',
        options: DELISTED_EXIT_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessExplicit,
      },
      {
        name: 'risk_control.skip_enter_when',
        type: 'checkboxGroup',
        label: '跳过进场如果股票是：',
        tooltip:
          '勾选后，价格/资金回测在触发日处于对应股票状态时跳过进场；枚举机会仍会保留。',
        options: skipOptions,
      },
      {
        name: 'risk_control.force_exit_when_draft.st.enabled',
        type: 'switch',
        label: '持仓遇 ST 强制出场',
        tooltip: '持仓期间进入 ST（含 SST）时触发强平规则。',
      },
      {
        name: 'risk_control.force_exit_when_draft.st.close_invest',
        type: 'switch',
        label: 'ST 触发清仓',
        tooltip: '开启后触发时全部卖出；关闭后可填写部分平仓比例。',
        visibleWhen: ({ values }) => Boolean(
          values?.risk_control?.force_exit_when_draft?.st?.enabled,
        ),
      },
      {
        name: 'risk_control.force_exit_when_draft.st.exit_ratio',
        type: 'number',
        label: 'ST 平仓比例',
        tooltip: '部分卖出比例（0～1）；开启「触发清仓」时不可编辑。',
        parse: parseNumber,
        visibleWhen: ({ values }) => Boolean(
          values?.risk_control?.force_exit_when_draft?.st?.enabled,
        ),
        readonlyWhen: ({ values }) => Boolean(
          values?.risk_control?.force_exit_when_draft?.st?.close_invest,
        ),
      },
      {
        name: 'risk_control.force_exit_when_draft.star_st.enabled',
        type: 'switch',
        label: '持仓遇 *ST 强制出场',
        tooltip: '持仓期间进入 *ST（含 S*ST）时触发强平规则。',
      },
      {
        name: 'risk_control.force_exit_when_draft.star_st.close_invest',
        type: 'switch',
        label: '*ST 触发清仓',
        visibleWhen: ({ values }) => Boolean(
          values?.risk_control?.force_exit_when_draft?.star_st?.enabled,
        ),
      },
      {
        name: 'risk_control.force_exit_when_draft.star_st.exit_ratio',
        type: 'number',
        label: '*ST 平仓比例',
        parse: parseNumber,
        visibleWhen: ({ values }) => Boolean(
          values?.risk_control?.force_exit_when_draft?.star_st?.enabled,
        ),
        readonlyWhen: ({ values }) => Boolean(
          values?.risk_control?.force_exit_when_draft?.star_st?.close_invest,
        ),
      },
    ],
  };
}

const strategySimulationSchema = buildStrategySimulationSchema();

export default strategySimulationSchema;
