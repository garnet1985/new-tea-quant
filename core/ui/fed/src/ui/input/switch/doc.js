const doc = {
  summary: '开关。默认标签在左、开关紧随其后（居左贴齐，不拉开）；onChange 为 e.target.checked。与 Checkbox（勾选确认）场景不同。',
  params: [
    {
      name: 'label',
      type: 'ReactNode',
      defaultValue: "''",
      description: '行内左侧文案。',
    },
    {
      name: 'fieldLabel / labelPlacement',
      type: '同 Field',
      defaultValue: "placement 'none'",
      description: '需要字段壳时用 fieldLabel + above/inline。',
    },
    {
      name: 'checked / onChange',
      type: '受控',
      defaultValue: '—',
      description: 'onChange(e) → e.target.checked。',
    },
    {
      name: 'tip / hint / error',
      type: 'ReactNode',
      defaultValue: '—',
      description: '无 Field 壳时 tip 跟在 label 旁；有壳时走 Field。',
    },
  ],
  scenarios: [
    '设置页即时开关、扫描选项、功能启停。',
  ],
  antiPatterns: [
    '表单「同意条款」类勾选用 Checkbox。',
  ],
};

export default doc;
