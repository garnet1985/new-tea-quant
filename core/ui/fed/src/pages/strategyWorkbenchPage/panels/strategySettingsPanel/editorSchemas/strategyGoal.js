const ACTION_NONE = '';
const ACTION_SET_PROTECT_LOSS = 'set_protect_loss';
const ACTION_SET_DYNAMIC_LOSS = 'set_dynamic_loss';

const STOCK_STATUS_RULE_NAMES = ['st', 'star_st'];

const STOCK_STATUS_RULE_META = {
  st: {
    label: 'ST（含 SST）',
    tooltip: '持仓期间进入 ST 状态时触发本规则。',
  },
  star_st: {
    label: '*ST（含 S*ST）',
    tooltip: '持仓期间进入 *ST 状态时触发本规则。',
  },
};

const TAKE_PROFIT_ACTION_OPTIONS = [
  { label: '不触发', value: ACTION_NONE },
  { label: '保本止损', value: ACTION_SET_PROTECT_LOSS },
  { label: '动态止损', value: ACTION_SET_DYNAMIC_LOSS },
];

function takeProfitActionFromStage(stage) {
  const actions = Array.isArray(stage?.actions) ? stage.actions : [];
  if (actions.includes(ACTION_SET_DYNAMIC_LOSS)) return ACTION_SET_DYNAMIC_LOSS;
  if (actions.includes(ACTION_SET_PROTECT_LOSS)) return ACTION_SET_PROTECT_LOSS;
  return ACTION_NONE;
}

function takeProfitActionsFromAction(action) {
  return action ? [action] : [];
}

function toNumberOrEmpty(value, fallback = '') {
  if (value === '' || value === null || value === undefined) return fallback;
  const n = Number(value);
  return Number.isNaN(n) ? fallback : n;
}

function normalizeStage(stage) {
  return {
    name: stage?.name || '',
    ratio: toNumberOrEmpty(stage?.ratio, ''),
    close_invest: Boolean(stage?.close_invest),
    sell_ratio: toNumberOrEmpty(stage?.sell_ratio, ''),
    actions: Array.isArray(stage?.actions) ? stage.actions : [],
    action: takeProfitActionFromStage(stage),
  };
}

function hasGoalExpiration(goal) {
  return goal?.expiration != null && typeof goal.expiration === 'object';
}

function readStockStatusRules(goal) {
  const raw = goal?.stock_status_risk_management;
  if (Array.isArray(raw)) return raw;
  if (raw && typeof raw === 'object' && Array.isArray(raw.rules)) return raw.rules;
  return [];
}

function normalizeStockStatusRuleDraft(rules, name) {
  const rule = rules.find((row) => String(row?.name || '').trim().toLowerCase() === name);
  if (!rule) {
    return { enabled: false, close_invest: true, sell_ratio: '' };
  }
  const closeInvest = rule.close_invest !== false ? Boolean(rule.close_invest) : false;
  return {
    enabled: true,
    close_invest: closeInvest,
    sell_ratio: closeInvest ? '' : toNumberOrEmpty(rule.sell_ratio, ''),
  };
}

function stockStatusRuleToPayload(draft, name) {
  if (!draft?.enabled) return null;
  if (Boolean(draft.close_invest)) {
    return { name, close_invest: true };
  }
  const ratio = toNumberOrEmpty(draft.sell_ratio, '');
  const payload = { name, close_invest: false };
  if (ratio !== '' && Number(ratio) > 0) {
    payload.sell_ratio = Number(ratio);
  }
  return payload;
}

export function normalizeGoalSettings(goal) {
  const expirationEnabled = hasGoalExpiration(goal);
  const stockStatusRules = readStockStatusRules(goal);
  return {
    expirationEnabled,
    expiration: {
      fixed_window_in_days: toNumberOrEmpty(
        expirationEnabled ? goal.expiration.fixed_window_in_days : undefined,
        30,
      ),
      is_trading_days: expirationEnabled
        ? goal.expiration.is_trading_days !== false
        : true,
    },
    stop_loss: {
      stages: Array.isArray(goal?.stop_loss?.stages)
        ? goal.stop_loss.stages.map(normalizeStage)
        : [],
    },
    take_profit: {
      stages: Array.isArray(goal?.take_profit?.stages)
        ? goal.take_profit.stages.map(normalizeStage)
        : [],
    },
    stock_status_risk_management: {
      st: normalizeStockStatusRuleDraft(stockStatusRules, 'st'),
      star_st: normalizeStockStatusRuleDraft(stockStatusRules, 'star_st'),
    },
    protect_loss: goal?.protect_loss
      ? {
          ratio: toNumberOrEmpty(goal.protect_loss.ratio, 0),
          close_invest: true,
        }
      : undefined,
    dynamic_loss: goal?.dynamic_loss
      ? {
          ratio: toNumberOrEmpty(goal.dynamic_loss.ratio, -0.1),
          close_invest: Boolean(goal.dynamic_loss.close_invest),
        }
      : undefined,
  };
}

function stageHasTakeProfitAction(stage, actionName) {
  if (stage?.action === actionName) return true;
  const actions = Array.isArray(stage?.actions) ? stage.actions : [];
  return actions.includes(actionName);
}

function hasTakeProfitAction(goal, actionName) {
  const stages = goal?.take_profit?.stages || [];
  return stages.some((stage) => stageHasTakeProfitAction(stage, actionName));
}

const hasProtectLossAction = ({ values }) => hasTakeProfitAction(values, ACTION_SET_PROTECT_LOSS);
const hasDynamicLossAction = ({ values }) => hasTakeProfitAction(values, ACTION_SET_DYNAMIC_LOSS);

export function applyGoalActions(goal) {
  const next = { ...(goal || {}) };
  const expirationEnabled = Boolean(next.expirationEnabled);
  const expDraft = next.expiration && typeof next.expiration === 'object'
    ? next.expiration
    : {};

  delete next.expirationEnabled;

  if (expirationEnabled) {
    const days = toNumberOrEmpty(expDraft.fixed_window_in_days, 30);
    next.expiration = {
      fixed_window_in_days: days === '' ? 30 : days,
      is_trading_days: expDraft.is_trading_days !== false,
    };
  } else {
    delete next.expiration;
  }

  const hasProtect = hasTakeProfitAction(next, ACTION_SET_PROTECT_LOSS);
  const hasDynamic = hasTakeProfitAction(next, ACTION_SET_DYNAMIC_LOSS);

  if (!hasProtect) {
    delete next.protect_loss;
  } else if (!next.protect_loss) {
    next.protect_loss = { ratio: 0, close_invest: true };
  } else {
    next.protect_loss = {
      ...next.protect_loss,
      close_invest: true,
    };
  }

  if (!hasDynamic) {
    delete next.dynamic_loss;
  } else if (!next.dynamic_loss) {
    next.dynamic_loss = { ratio: -0.1, close_invest: true };
  }

  if (next.take_profit?.stages) {
    next.take_profit = {
      ...next.take_profit,
      stages: next.take_profit.stages.map((stage) => {
        const { action, ...rest } = stage;
        return { ...rest, actions: takeProfitActionsFromAction(action) };
      }),
    };
  }

  if (next.stop_loss?.stages) {
    next.stop_loss = {
      ...next.stop_loss,
      stages: next.stop_loss.stages.map(({ action, ...rest }) => rest),
    };
  }

  const stockStatusDraft = next.stock_status_risk_management;
  delete next.stock_status_risk_management;
  const stockStatusRules = STOCK_STATUS_RULE_NAMES
    .map((name) => stockStatusRuleToPayload(stockStatusDraft?.[name], name))
    .filter(Boolean);
  if (stockStatusRules.length > 0) {
    next.stock_status_risk_management = { rules: stockStatusRules };
  }

  return next;
}

const goalExpirationEnabled = ({ values }) => Boolean(values?.expirationEnabled);

const stockStatusRuleEnabled = (name) => ({ values }) => (
  Boolean(values?.stock_status_risk_management?.[name]?.enabled)
);

const stockStatusRuleSellRatioReadonly = (name) => ({ values }) => (
  Boolean(values?.stock_status_risk_management?.[name]?.close_invest)
);

function buildStockStatusRuleFields(name) {
  const meta = STOCK_STATUS_RULE_META[name];
  return [
    {
      name: `stock_status_risk_management.${name}.enabled`,
      type: 'switch',
      label: '启用规则',
      tooltip: meta.tooltip,
    },
    {
      name: `stock_status_risk_management.${name}.close_invest`,
      type: 'switch',
      label: '触发清仓',
      tooltip: '开启后触发时全部卖出；关闭后可填写部分平仓比例。',
      visibleWhen: stockStatusRuleEnabled(name),
    },
    {
      name: `stock_status_risk_management.${name}.sell_ratio`,
      type: 'number',
      label: '平仓比例',
      tooltip: '部分卖出比例（0～1 的小数）；开启「触发清仓」时不可编辑。',
      parse: (raw) => toNumberOrEmpty(raw, ''),
      visibleWhen: stockStatusRuleEnabled(name),
      readonlyWhen: stockStatusRuleSellRatioReadonly(name),
    },
  ];
}

const goalBaseFields = [
  {
    name: 'expirationEnabled',
    type: 'switch',
    label: '开启交易时限',
    tooltip: '管理是否需要按照日期进行强制平仓',
  },
  {
    name: 'expiration.fixed_window_in_days',
    type: 'number',
    label: '到期窗口天数',
    tooltip: '指过去多少个交易日或工作日后自动平仓，是自然日还是交易日请在「是否按照交易日计数」里设置',
    parse: (raw) => toNumberOrEmpty(raw, ''),
    visibleWhen: goalExpirationEnabled,
  },
  {
    name: 'expiration.is_trading_days',
    type: 'switch',
    label: '是否按照交易日计数',
    tooltip: '如果不是开启按照交易日计算，那么回测到期则会按照自然日计数',
    visibleWhen: goalExpirationEnabled,
  },
];

const protectLossFields = [
  {
    name: 'protect_loss.ratio',
    type: 'number',
    label: '回撤到本金比例',
    helperText: '支持小数，例如 0.02 表示达到保本目标后回撤 2% 清仓。',
    parse: (raw) => toNumberOrEmpty(raw, ''),
    visibleWhen: hasProtectLossAction,
  },
];

const dynamicLossFields = [
  {
    name: 'dynamic_loss.ratio',
    type: 'number',
    label: '可承受最大回撤比例',
    parse: (raw) => toNumberOrEmpty(raw, ''),
    visibleWhen: hasDynamicLossAction,
  },
  {
    name: 'dynamic_loss.close_invest',
    type: 'switch',
    label: '动态止损触发清仓',
    visibleWhen: hasDynamicLossAction,
  },
];

const goalStageSchemas = [
  {
    key: 'stop_loss',
    title: '止损阶段（stop_loss.stages）',
    name: 'stop_loss.stages',
    initValue: () => ({
      name: '',
      ratio: '',
      close_invest: false,
      sell_ratio: '',
      actions: [],
    }),
    template: [
      {
        key: 'name',
        type: 'text',
        label: '阶段名称',
        tooltip: '给这个阶段起个可读的名字',
      },
      {
        key: 'ratio',
        type: 'number',
        label: '触发比例',
        tooltip:
          '当持仓相对买入价的盈亏达到该比例时触发本阶段（止损填负数，如 -0.1 表示亏损 10%）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
      },
      {
        key: 'sell_ratio',
        type: 'number',
        label: '平仓比例',
        tooltip: '这个阶段完成时卖出多少仓位，用小数表示百分比（0～1）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
        visibleWhen: ({ item }) => !item?.close_invest,
      },
      { key: 'close_invest', type: 'switch', label: '触发清仓' },
    ],
  },
  {
    key: 'take_profit',
    title: '止盈阶段（take_profit.stages）',
    name: 'take_profit.stages',
    initValue: () => ({
      name: '',
      ratio: '',
      close_invest: false,
      sell_ratio: '',
      actions: [],
      action: ACTION_NONE,
    }),
    template: [
      {
        key: 'name',
        type: 'text',
        label: '阶段名称',
        tooltip: '给这个阶段起个可读的名字',
      },
      {
        key: 'ratio',
        type: 'number',
        label: '触发比例',
        tooltip:
          '当持仓相对买入价的盈亏达到该比例时触发本阶段（止盈填正数，如 0.1 表示盈利 10%）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
      },
      {
        key: 'sell_ratio',
        type: 'number',
        label: '平仓比例',
        tooltip: '这个阶段完成时卖出多少仓位，用小数表示百分比（0～1）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
        visibleWhen: ({ item }) => !item?.close_invest,
      },
      { key: 'close_invest', type: 'switch', label: '触发清仓' },
      {
        key: 'action',
        type: 'select',
        label: '触发动作',
        options: TAKE_PROFIT_ACTION_OPTIONS,
      },
    ],
  },
];

function toEditorField(field) {
  return {
    name: field.name,
    type: field.type,
    label: field.label,
    tooltip: field.tooltip || '',
    description: field.helperText || field.description || '',
    parse: field.parse,
    visibleWhen: field.visibleWhen,
    readonlyWhen: field.readonlyWhen,
    options: field.options,
    multiple: field.multiple,
  };
}

function toFieldCollection(stageSchema) {
  return {
    name: stageSchema.name,
    type: 'fieldCollection',
    label: '',
    embedded: true,
    initValue: stageSchema.initValue,
    template: stageSchema.template,
    addLabel: '增加阶段目标',
    removeLabel: '删除阶段目标',
    emptyText: '暂无阶段目标，请点击「增加阶段目标」。',
  };
}

const stopLossStageSchema = goalStageSchemas.find((s) => s.key === 'stop_loss');
const takeProfitStageSchema = goalStageSchemas.find((s) => s.key === 'take_profit');

const strategyGoalSchema = {
  name: 'strategyGoal',
  type: 'fieldGroup',
  label: '',
  children: [
    {
      name: 'strategyGoal.base',
      type: 'fieldGroup',
      label: '到期设置',
      tooltip: '给投资加上一个时间期限，到了时限自动结束交易，无论输赢。',
      children: goalBaseFields.map(toEditorField),
    },
    {
      name: 'strategyGoal.stopLoss',
      type: 'fieldGroup',
      label: '设置止损',
      tooltip: '设置止损目标，可以分为多个阶段。',
      children: [toFieldCollection(stopLossStageSchema)],
    },
    {
      name: 'strategyGoal.takeProfit',
      type: 'fieldGroup',
      label: '设置止盈',
      tooltip: '设置止盈目标，可以分为多个阶段。',
      children: [toFieldCollection(takeProfitStageSchema)],
    },
    {
      name: 'strategyGoal.actionDerived.protectLoss',
      type: 'fieldGroup',
      label: '保本止损设置',
      visibleWhen: hasProtectLossAction,
      children: protectLossFields.map(toEditorField),
    },
    {
      name: 'strategyGoal.actionDerived.dynamicLoss',
      type: 'fieldGroup',
      label: '动态止损设置',
      visibleWhen: hasDynamicLossAction,
      children: dynamicLossFields.map(toEditorField),
    },
    {
      name: 'strategyGoal.stockStatusRisk',
      type: 'fieldGroup',
      label: '股票状态风险管控',
      tooltip: '持仓期间遇 ST/*ST 时的强平规则；退市强平由引擎默认启用，不可关闭。',
      children: STOCK_STATUS_RULE_NAMES.map((name) => ({
        name: `strategyGoal.stockStatusRisk.${name}`,
        type: 'fieldGroup',
        label: STOCK_STATUS_RULE_META[name].label,
        tooltip: STOCK_STATUS_RULE_META[name].tooltip,
        children: buildStockStatusRuleFields(name).map(toEditorField),
      })),
    },
  ],
};

export default strategyGoalSchema;
