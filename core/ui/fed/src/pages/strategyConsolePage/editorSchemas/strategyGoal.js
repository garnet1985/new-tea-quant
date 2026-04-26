const ACTION_SET_PROTECT_LOSS = 'set_protect_loss';
const ACTION_SET_DYNAMIC_LOSS = 'set_dynamic_loss';

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
  };
}

export function normalizeGoalSettings(goal) {
  return {
    expiration: {
      fixed_window_in_days: toNumberOrEmpty(goal?.expiration?.fixed_window_in_days, 30),
      is_trading_days: goal?.expiration?.is_trading_days !== false,
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

function hasTakeProfitAction(goal, actionName) {
  const stages = goal?.take_profit?.stages || [];
  return stages.some((stage) => Array.isArray(stage.actions) && stage.actions.includes(actionName));
}

export function applyGoalActions(goal) {
  const next = { ...(goal || {}) };
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

  return next;
}

const goalBaseFields = [
  {
    name: 'expiration.fixed_window_in_days',
    type: 'number',
    label: '到期窗口天数',
    parse: (raw) => toNumberOrEmpty(raw, ''),
  },
  {
    name: 'expiration.is_trading_days',
    type: 'switch',
    label: '按交易日计数',
  },
];

const protectLossFields = [
  {
    name: 'protect_loss.ratio',
    type: 'number',
    label: '回撤到本金比例',
    helperText: '支持小数，例如 0.02 表示达到保本目标后回撤 2% 清仓。',
    parse: (raw) => toNumberOrEmpty(raw, ''),
    visibleWhen: ({ values }) => hasTakeProfitAction(values, ACTION_SET_PROTECT_LOSS),
  },
];

const dynamicLossFields = [
  {
    name: 'dynamic_loss.ratio',
    type: 'number',
    label: '可承受最大回撤比例',
    parse: (raw) => toNumberOrEmpty(raw, ''),
    visibleWhen: ({ values }) => hasTakeProfitAction(values, ACTION_SET_DYNAMIC_LOSS),
  },
  {
    name: 'dynamic_loss.close_invest',
    type: 'switch',
    label: '动态止损触发清仓',
    visibleWhen: ({ values }) => hasTakeProfitAction(values, ACTION_SET_DYNAMIC_LOSS),
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
      { key: 'name', type: 'text', label: '阶段名称' },
      {
        key: 'ratio',
        type: 'number',
        label: '触发比例',
        parse: (raw) => toNumberOrEmpty(raw, ''),
      },
      { key: 'close_invest', type: 'switch', label: '触发清仓' },
      {
        key: 'sell_ratio',
        type: 'number',
        label: '卖出比例（0~1）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
        visibleWhen: ({ item }) => !item?.close_invest,
      },
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
    }),
    template: [
      { key: 'name', type: 'text', label: '阶段名称' },
      {
        key: 'ratio',
        type: 'number',
        label: '触发比例',
        parse: (raw) => toNumberOrEmpty(raw, ''),
      },
      { key: 'close_invest', type: 'switch', label: '触发清仓' },
      {
        key: 'sell_ratio',
        type: 'number',
        label: '卖出比例（0~1）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
        visibleWhen: ({ item }) => !item?.close_invest,
      },
      {
        key: 'actions',
        type: 'select',
        label: '触发动作',
        multiple: true,
        options: [
          { label: ACTION_SET_PROTECT_LOSS, value: ACTION_SET_PROTECT_LOSS },
          { label: ACTION_SET_DYNAMIC_LOSS, value: ACTION_SET_DYNAMIC_LOSS },
        ],
      },
    ],
  },
];

function toEditorField(field) {
  return {
    name: field.name,
    type: field.type,
    label: field.label,
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
    label: stageSchema.title,
    initValue: stageSchema.initValue,
    template: stageSchema.template,
    addLabel: '新增阶段',
    emptyText: '暂无阶段，请点击“新增阶段”。',
  };
}

const strategyGoalSchema = {
  name: 'strategyGoal',
  type: 'fieldGroup',
  label: '',
  children: [
    {
      name: 'strategyGoal.base',
      type: 'fieldGroup',
      label: '到期设置',
      children: goalBaseFields.map(toEditorField),
    },
    ...goalStageSchemas.map(toFieldCollection),
    {
      name: 'strategyGoal.actionDerived.protectLoss',
      type: 'fieldGroup',
      label: '保本止损设置',
      children: protectLossFields.map(toEditorField),
    },
    {
      name: 'strategyGoal.actionDerived.dynamicLoss',
      type: 'fieldGroup',
      label: '动态止损设置',
      children: dynamicLossFields.map(toEditorField),
    },
  ],
};

export default strategyGoalSchema;
