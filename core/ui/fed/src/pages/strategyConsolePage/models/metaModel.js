export function normalizeMeta(rawMeta) {
  return {
    name: rawMeta?.name || '',
    description: rawMeta?.description || '',
    is_enabled: Boolean(rawMeta?.is_enabled),
  };
}

export const metaSectionModel = {
  sectionKey: 'meta',
  sectionTitle: 'Meta 信息',
  defaultExpanded: true,
};
