const doc = {
  summary: '日期区间。value 为 { start, end }（YYYY-MM-DD）；onChange 为 e.target.value。',
  params: [
    {
      name: 'label / labelPlacement / tip / hint / error',
      type: '同 Field',
      defaultValue: '—',
      description: '整段字段壳。',
    },
    {
      name: 'value / onChange',
      type: '{ start, end }',
      defaultValue: '—',
      description: '受控区间；onChange(e) → e.target.value。',
    },
    {
      name: 'startLabel / endLabel',
      type: 'string',
      defaultValue: "'开始' / '结束'",
      description: '无外层 label 时，两个 Date 各自的标签。',
    },
    {
      name: 'startError / endError',
      type: 'ReactNode',
      defaultValue: '—',
      description: '单侧校验文案。',
    },
  ],
  scenarios: [
    '回测区间、报表起止日。',
  ],
  antiPatterns: [
    '单日用 Date。',
  ],
};

export default doc;
