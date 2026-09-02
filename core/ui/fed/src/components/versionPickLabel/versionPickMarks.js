export const VERSION_MARK_READONLY = '仅供查阅';
export const VERSION_MARK_EXPIRES_SOON = '即将清理';

export const VERSION_MARK_HINTS = {
  readonly: '环境已更新，这份产物仅供查阅；仍可恢复当时配置。',
  expires: '保留额度触顶后会优先清理该版本。',
};

export function versionPickMarks(version) {
  if (!version || typeof version !== 'object') return [];
  const marks = [];
  if (version.envInvalid) {
    marks.push({
      key: 'readonly',
      label: VERSION_MARK_READONLY,
      hint: VERSION_MARK_HINTS.readonly,
    });
  }
  if (version.expiresSoon) {
    marks.push({
      key: 'expires',
      label: VERSION_MARK_EXPIRES_SOON,
      hint: VERSION_MARK_HINTS.expires,
    });
  }
  return marks;
}

export function lookupVersionById(versions, id) {
  const vid = String(id ?? '').trim();
  const rows = Array.isArray(versions) ? versions : [];
  return rows.find((row) => row.id === vid) || { id: vid };
}

export function versionPickSearchText(version) {
  const marks = versionPickMarks(version).map((mark) => mark.label).join(' ');
  return [
    version?.id,
    version?.createdAt,
    version?.updatedAt,
    marks,
  ].filter(Boolean).join(' ');
}
