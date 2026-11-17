const doc = {
  summary: '基础下拉（MUI Select）。options 为 { value, label }[]；标签走 Field。onChange 用 e.target.value。',
  params: [
    {
      name: 'label / labelPlacement / tip / hint / error',
      type: '同 Field',
      defaultValue: '—',
      description: '字段壳。',
    },
    {
      name: 'options',
      type: '{ value, label, disabled? }[]',
      defaultValue: '[]',
      description: '选项。',
    },
    {
      name: 'value / onChange',
      type: '受控',
      defaultValue: '—',
      description: '单选为标量；multiple 时为数组。',
    },
    {
      name: 'placeholder',
      type: 'string',
      defaultValue: "'请选择'",
      description: '空值展示。',
    },
    {
      name: 'multiple',
      type: 'boolean',
      defaultValue: 'false',
      description: '多选。',
    },
    {
      name: 'disabled',
      type: 'boolean',
      defaultValue: 'false',
      description: '禁用。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 280px 上限；false 去掉。',
    },
  ],
  scenarios: [
    '表单枚举：周期、模式、档位。',
  ],
  antiPatterns: [
    '选项很多且需筛选时用 SearchSelect。',
    '禁止写死像素宽度；用 maxWidth={false} 或父布局。',
  ],
};

export default doc;
