export function normalizeMeta(rawMeta) {
  return {
    name: rawMeta?.name || '',
    description: rawMeta?.description || '',
    is_enabled: Boolean(rawMeta?.is_enabled),
  };
}

export const metaSectionModel = {
  sectionKey: 'meta',
  sectionTitle: '策略基本信息',
  defaultExpanded: true,
};
