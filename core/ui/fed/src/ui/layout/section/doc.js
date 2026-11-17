const doc = {
  summary: '纵向分区原语。gap 只用语义 token（--ntq-space-*）。',
  params: [
    {
      name: 'gap',
      type: "'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'",
      defaultValue: "'md'",
      description: '子块垂直间距 token。',
    },
    {
      name: 'children',
      type: 'ReactNode',
      defaultValue: '—',
      description: '分区内容。',
    },
  ],
  scenarios: [
    '上下排列多组 Block / Column。',
    '组合：Section → Column → Block。',
  ],
  antiPatterns: [
    '禁止 gap={24}。',
    '横向分栏用 Column。',
  ],
};

export default doc;
