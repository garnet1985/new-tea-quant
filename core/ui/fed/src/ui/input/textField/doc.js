const doc = {
  summary: '单行文本输入（MUI TextField + 玻璃态）。标签 / tip / hint / error 走 Field。',
  params: [
    {
      name: 'label',
      type: 'ReactNode',
      defaultValue: "''",
      description: '字段标签。',
    },
    {
      name: 'labelPlacement',
      type: "'above' | 'inline' | 'none'",
      defaultValue: "'above'",
      description: '标签位置。',
    },
    {
      name: 'value / onChange',
      type: '受控',
      defaultValue: '—',
      description: '与原生 input 一致。',
    },
    {
      name: 'type',
      type: 'string',
      defaultValue: "'text'",
      description: '如 text / number / password。',
    },
    {
      name: 'tip / hint / error',
      type: 'ReactNode',
      defaultValue: '—',
      description: '说明与校验。',
    },
    {
      name: 'disabled / placeholder / required',
      type: '常用',
      defaultValue: '—',
      description: '禁用、占位、必填标记。',
    },
    {
      name: 'maxWidth',
      type: 'boolean',
      defaultValue: 'true',
      description: '默认约 280px 上限；false 去掉，随父级拉满。',
    },
  ],
  scenarios: [
    '表单短文本、数字、密码。',
  ],
  antiPatterns: [
    '多行请用 TextArea。',
    '禁止传入像素 height。',
  ],
};

export default doc;
