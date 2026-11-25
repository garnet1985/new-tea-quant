const doc = {
  summary: '单行文本输入（MUI TextField + 深色实底）。标签 / tip / hint / error 走 Field。',
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
      description: '默认约 320px 上限；false 去掉，随父级拉满。',
    },
    {
      name: 'surface',
      type: "'solid' | 'glass'",
      defaultValue: "'solid'",
      description: '默认 solid 深色实底；glass=半透明玻璃。',
    },
    {
      name: 'radius',
      type: "'sm' | 'none'",
      defaultValue: "'sm'",
      description: '扩展：sm=现有圆角；none=直角。',
    },
  ],
  scenarios: [
    '表单短文本、数字、密码。',
    '直角：radius="none"。需玻璃时 surface="glass"。',
  ],
  antiPatterns: [
    '多行请用 TextArea。',
    '禁止传入像素 height。',
  ],
};

export default doc;
