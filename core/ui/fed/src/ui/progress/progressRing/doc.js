const doc = {
  summary: '圆环进度（对齐回测 step 环）。value 0–100；不传为不确定旋转。可选 label（step 名）与 showPercent；children 可覆盖环心。',
  params: [
    {
      name: 'value',
      type: 'number | null',
      defaultValue: 'null',
      description: '0–100；null 表示 indeterminate。',
    },
    {
      name: 'size',
      type: "'sm' | 'md'",
      defaultValue: "'md'",
      description: '外径 token → --ntq-progress-ring-*（md ≈ 回测 56px）。',
    },
    {
      name: 'label',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '环下方文案，如 step 名。',
    },
    {
      name: 'showPercent',
      type: 'boolean',
      defaultValue: 'false',
      description: '环心显示取整百分比（有 children 时以 children 为准）。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: 'null',
      description: '自定义环心（如步骤号）。',
    },
  ],
  scenarios: [
    '回测步骤运行中：value={pct} showPercent。',
    '步骤环心放编号：children={no}。',
    '未知进度：不传 value。',
  ],
  antiPatterns: [
    '禁止 size={56} 写死像素。',
    '整页加载优先 Loading；有明确百分比再用 ProgressRing / ProgressBar。',
  ],
};

export default doc;
