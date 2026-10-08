function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

const feeFieldDefs = [
  {
    name: 'commission_rate',
    label: '佣金率',
    tooltip: '券商佣金占成交金额的比例，例如 0.00025 表示万分之 2.5。',
  },
  {
    name: 'min_commission',
    label: '最低佣金',
    tooltip: '单笔交易佣金的下限（元）；按比例算出的佣金低于该值时，按此金额收取。',
  },
  {
    name: 'stamp_duty_rate',
    label: '印花税率',
    tooltip: '卖出时按成交金额征收的印花税比例，仅卖出侧计费；买入为 0。',
  },
  {
    name: 'transfer_fee_rate',
    label: '过户费率',
    tooltip: '按成交金额收取的过户费比例，买入与卖出均计入（A 股常见为 0 或由券商代扣）。',
  },
];

function toFeeField({ name, label, tooltip }, { readonly = false } = {}) {
  return {
    name,
    type: 'number',
    label,
    tooltip,
    parse: parseNumber,
    readonly,
  };
}

export function createStrategyFeesSchema({ readonly = false } = {}) {
  return {
    name: 'strategyFees',
    type: 'fieldGroup',
    label: '',
    children: feeFieldDefs.map((def) => toFeeField(def, { readonly })),
  };
}

const strategyFeesSchema = createStrategyFeesSchema();

export default strategyFeesSchema;
