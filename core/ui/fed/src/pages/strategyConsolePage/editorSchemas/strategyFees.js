function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

export function createStrategyFeesSchema({ readonly = false } = {}) {
  return {
    name: 'strategyFees',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'commission_rate',
        type: 'number',
        label: '佣金率 (commission_rate)',
        parse: parseNumber,
        readonly,
      },
      {
        name: 'min_commission',
        type: 'number',
        label: '最低佣金 (min_commission)',
        parse: parseNumber,
        readonly,
      },
      {
        name: 'stamp_duty_rate',
        type: 'number',
        label: '印花税率 (stamp_duty_rate)',
        parse: parseNumber,
        readonly,
      },
      {
        name: 'transfer_fee_rate',
        type: 'number',
        label: '过户费率 (transfer_fee_rate)',
        parse: parseNumber,
        readonly,
      },
    ],
  };
}

const strategyFeesSchema = createStrategyFeesSchema();

export default strategyFeesSchema;
