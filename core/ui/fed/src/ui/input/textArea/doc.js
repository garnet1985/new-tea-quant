const doc = {
  summary: '多行文本（MUI TextField multiline）。标签布局同 TextField；rows 默认 4。',
  params: [
    {
      name: 'label / labelPlacement / tip / hint / error',
      type: '同 Field',
      defaultValue: '—',
      description: '字段壳。',
    },
    {
      name: 'rows',
      type: 'number',
      defaultValue: '3',
      description: '最小行数（业务数据，非样式像素）。',
    },
    {
      name: 'value / onChange / placeholder / disabled',
      type: '受控常用',
      defaultValue: '—',
      description: '同单行。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 280px 上限；false 去掉。',
    },
  ],
  scenarios: [
    '备注、说明、多行配置文案。',
  ],
  antiPatterns: [
    '单行请用 TextField。',
    '禁止用 style 写死高度像素。',
  ],
};

export default doc;
