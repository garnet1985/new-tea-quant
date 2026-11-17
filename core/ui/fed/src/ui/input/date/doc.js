const doc = {
  summary: '单日日期（原生 type=date）。value 为 YYYY-MM-DD；onChange 为 e.target.value。',
  params: [
    {
      name: 'label / labelPlacement / tip / hint / error',
      type: '同 Field',
      defaultValue: '—',
      description: '字段壳。',
    },
    {
      name: 'value / onChange',
      type: '受控',
      defaultValue: '—',
      description: '字符串日期；空为 \'\'。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 320px；false 去掉。',
    },
  ],
  scenarios: [
    '单个交易日、生效日。',
  ],
  antiPatterns: [
    '起止区间用 DateRange。',
    '禁止自写像素日历；需要复杂选日再另议。',
  ],
};

export default doc;
