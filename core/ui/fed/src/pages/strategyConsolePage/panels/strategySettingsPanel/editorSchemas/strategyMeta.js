export function normalizeMeta(rawMeta) {
  return {
    name: rawMeta?.name || '',
    description: rawMeta?.description || '',
    is_enabled: Boolean(rawMeta?.is_enabled),
  };
}

const strategyMetaSchema = {
  name: 'strategyMeta',
  label: '策略基本信息',
  description: '启用状态与全局模拟窗口',
  type: 'section',
  defaultExpanded: true,
  children: [
    {
      name: 'meta.is_enabled',
      label: '是否启用策略',
      description: '控制策略启用状态',
      type: 'switch',
    },
    {
      name: 'meta.simulationWindow',
      label: '模拟时间段',
      description: '同一时间段会同步到价格回测和资金模拟',
      type: 'columns',
      columns: 1,
      children: [
        {
          name: 'meta.simulationDateRange',
          label: '模拟时间段',
          description: '结束日期不能早于开始日期',
          type: 'dateRange',
          startName: 'price_simulator.start_date',
          endName: 'price_simulator.end_date',
          startLabel: 'From',
          endLabel: 'To',
          syncTargets: [
            {
              startName: 'capital_simulator.start_date',
              endName: 'capital_simulator.end_date',
            },
          ],
        },
      ],
    },
    {
      name: 'data.min_required_records',
      label: '最小K线记录数',
      description: '至少满足该历史记录条数才执行策略（默认 100）',
      type: 'number',
    },
  ],
};

export default strategyMetaSchema;
