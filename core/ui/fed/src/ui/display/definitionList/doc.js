const doc = {
  summary: '只读键值行。用于详情弹层、摘要条；不是表单 Field。',
  params: [
    {
      name: 'items',
      type: 'Array<{ label, value, key? }>',
      defaultValue: '[]',
      description: '每行一个 label + value（value 可为 ReactNode）。',
    },
  ],
  scenarios: [
    '持仓 / 成交明细弹层。',
    '决策 HUD 现金与持仓摘要。',
  ],
  antiPatterns: [
    '可编辑字段用 Field / TextField，不要用 DefinitionList。',
    '大段说明用 TextBlock / DescriptionText。',
  ],
};

export default doc;
