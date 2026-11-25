const doc = {
  summary: '表单字段壳：标签 above / inline / none，可选 tip（HelpTooltip）、hint、error。标签/控件/错误文案间距为 space sm。各输入控件内部可组合本组件。',
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
      description: '标签在上 / 左 / 不显示。',
    },
    {
      name: 'tip',
      type: 'ReactNode',
      defaultValue: "''",
      description: '标签旁帮助气泡。',
    },
    {
      name: 'hint',
      type: 'ReactNode',
      defaultValue: "''",
      description: '辅助说明（无 error 时显示）。',
    },
    {
      name: 'error',
      type: 'ReactNode',
      defaultValue: "''",
      description: '错误文案（优先于 hint）。',
    },
    {
      name: 'htmlFor',
      type: "string | false",
      defaultValue: '自动',
      description: 'label[for] 目标 id；false 时改走 aria-labelledby（RadioGroup 等）。',
    },
    {
      name: 'required',
      type: 'boolean',
      defaultValue: 'false',
      description: '标签后显示 *。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '控件本体。',
    },
  ],
  scenarios: [
    '表单字段统一标签与错误展示。',
    '紧凑行：labelPlacement="inline"。',
  ],
  antiPatterns: [
    '不要在业务里再手写一套 label 布局。',
    '不要用 Field 包非表单装饰块。',
  ],
};

export default doc;
