const ACTION_NONE = '';
const ACTION_SET_PROTECT_LOSS = 'set_protect_loss';
const ACTION_SET_DYNAMIC_LOSS = 'set_dynamic_loss';

const TAKE_PROFIT_ACTION_OPTIONS = [
  { label: '不触发', value: ACTION_NONE },
  { label: '保本止损', value: ACTION_SET_PROTECT_LOSS },
  { label: '动态止损', value: ACTION_SET_DYNAMIC_LOSS },
];

const EXPIRATION_MODE_OPTIONS = [
  {
    label: '开市日',
    value: 'open_day',
    tooltip: '按开市日计数持有期（与 Investment 一致，常用）。',
  },
  {
    label: '交易日',
    value: 'trading_day',
    tooltip: '按交易日计数持有期。',
  },
  {
    label: '自然日',
    value: 'natural_day',
    tooltip: '按自然日计数持有期。',
  },
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

function normalizeExpirationMode(expiration) {
  if (!expiration || typeof expiration !== 'object') return 'open_day';
  if (expiration.mode) return String(expiration.mode);
  if (expiration.is_trading_days === false) return 'natural_day';
  if (expiration.is_trading_days === true) return 'trading_day';
  return 'open_day';
}

/** settings 不写 name；运行期按 ratio 推断（-0.1→loss10%，0.1→win10%）。 */
function stripStageName(stage) {
  if (!stage || typeof stage !== 'object') return stage;
  const next = { ...stage };
  delete next.name;
  delete next._inferredName;
  return next;
}

/** 与 GoalSettings._to_stage_name 对齐（Python `{pct:g}`）。 */
function formatPctG(value) {
  if (!Number.isFinite(value)) return '';
  return String(Number(value.toPrecision(12)));
}

export function inferStageName(ratio, kind = 'stop_loss') {
  if (ratio === '' || ratio === null || ratio === undefined) return '';
  const n = Number(ratio);
  if (!Number.isFinite(n)) return '';
  const pct = formatPctG(Math.abs(n) * 100);
  if (kind === 'take_profit' || n > 0) return `win${pct}%`;
  if (n < 0) return `loss${pct}%`;
  return `level${pct}%`;
}

function inferredNameField(kind) {
  return {
    key: '_inferredName',
    type: 'display',
    label: '阶段名称',
    tooltip: '由触发比例自动推断（settings 不写 name），不可编辑。',
    placeholder: ' ',
    resolve: ({ item }) => inferStageName(item?.ratio, kind),
  };
}

function normalizeStage(stage) {
  const exitRatio = stage?.exit_ratio !== undefined
    ? stage.exit_ratio
    : stage?.sell_ratio;
  return {
    ratio: toNumberOrEmpty(stage?.ratio, ''),
    close_invest: Boolean(stage?.close_invest),
    exit_ratio: toNumberOrEmpty(exitRatio, ''),
    actions: Array.isArray(stage?.actions) ? stage.actions : [],
    action: takeProfitActionFromStage(stage),
  };
}

function hasGoalExpiration(goal) {
  return goal?.expiration != null && typeof goal.expiration === 'object';
}

export function normalizeGoalSettings(goal) {
  const expirationEnabled = hasGoalExpiration(goal);
  return {
    expirationEnabled,
    expiration: {
      fixed_window_in_days: toNumberOrEmpty(
        expirationEnabled ? goal.expiration.fixed_window_in_days : undefined,
        30,
      ),
      mode: expirationEnabled ? normalizeExpirationMode(goal.expiration) : 'open_day',
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
      mode: expDraft.mode || 'open_day',
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
        return stripStageName({ ...rest, actions: takeProfitActionsFromAction(action) });
      }),
    };
  }

  if (next.stop_loss?.stages) {
    next.stop_loss = {
      ...next.stop_loss,
      stages: next.stop_loss.stages.map(({ action, ...rest }) => stripStageName(rest)),
    };
  }

  // 股票状态风控已迁至 simulation.risk_control
  delete next.stock_status_risk_management;

  return next;
}

const goalExpirationEnabled = ({ values }) => Boolean(values?.expirationEnabled);

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
    tooltip: '持有多少天后自动平仓；计数口径见「到期计数模式」。',
    parse: (raw) => toNumberOrEmpty(raw, ''),
    visibleWhen: goalExpirationEnabled,
  },
  {
    name: 'expiration.mode',
    type: 'select',
    label: '到期计数模式',
    tooltip: 'open_day / trading_day / natural_day，与 Investment 持有期计数一致。',
    options: EXPIRATION_MODE_OPTIONS,
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
      ratio: '',
      close_invest: false,
      exit_ratio: '',
      actions: [],
    }),
    template: [
      inferredNameField('stop_loss'),
      {
        key: 'ratio',
        type: 'number',
        label: '触发比例',
        tooltip:
          '当持仓相对买入价的盈亏达到该比例时触发本阶段（止损填负数，如 -0.1 表示亏损 10%；上方名称自动推断为 loss10%）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
      },
      {
        key: 'exit_ratio',
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
      ratio: '',
      close_invest: false,
      exit_ratio: '',
      actions: [],
      action: ACTION_NONE,
    }),
    template: [
      inferredNameField('take_profit'),
      {
        key: 'ratio',
        type: 'number',
        label: '触发比例',
        tooltip:
          '当持仓相对买入价的盈亏达到该比例时触发本阶段（止盈填正数，如 0.1 表示盈利 10%；上方名称自动推断为 win10%）',
        parse: (raw) => toNumberOrEmpty(raw, ''),
      },
      {
        key: 'exit_ratio',
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
  ],
};

export default strategyGoalSchema;
