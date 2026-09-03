import { formatDateTime, formatVersionPickTime } from '../../utils/formatDateTime';

export const VERSION_MARK_READONLY = '仅供查阅';
export const VERSION_MARK_EXPIRES_SOON = '即将清理';
export const SETTINGS_RETENTION_HREF = '/settings/data#retention';

export const VERSION_MARK_READONLY_HINT = [
  '当前版本是在以前的运行环境中生成的并且已经无法在当前环境继续使用。',
  '可能的原因包括软件升级、回测引擎或数据合约更新、代码发生变动等等。',
  '这个版本目录和结果将会变成只读，如果恢复到此版本可能结果将会是无法运行或者产生新的衍生版本。',
].join('');

export function versionMarkExpiresHint(retentionMax) {
  const n = Number(retentionMax);
  const capText = Number.isFinite(n) && n > 0
    ? `系统目前最多保留 ${n} 份回测结果。`
    : '系统只保留有限数量的回测结果。';
  return [
    '不是按日历过期，而是按保留份数。',
    capText,
    '额度用满后再产生新版本并触发清理时，更旧、未固定的版本会优先被删掉。',
    '当前在制定策略里新回测额度满时会先拒绝写入，避免悄悄删掉结果；扫描等流程会按上限自动裁剪。',
    '调整保留份数请到设置 → 数据范围。',
  ].join('');
}

export function retentionCapFromVersions(versions) {
  const rows = Array.isArray(versions) ? versions : [];
  for (let i = 0; i < rows.length; i += 1) {
    const n = Number(rows[i]?.retentionMax);
    if (Number.isFinite(n) && n > 0) return n;
  }
  return 0;
}

export function formatRetentionCapLabel(retentionMax) {
  const n = Number(retentionMax);
  if (Number.isFinite(n) && n > 0) return `当前设置最多保留 「${n}」个版本`;
  return '当前设置按份数保留版本';
}

export function versionPickMarks(version) {
  if (!version || typeof version !== 'object') return [];
  const marks = [];
  if (version.envInvalid) {
    marks.push({
      key: 'readonly',
      label: VERSION_MARK_READONLY,
      hint: VERSION_MARK_READONLY_HINT,
    });
  }
  if (version.expiresSoon) {
    marks.push({
      key: 'expires',
      label: VERSION_MARK_EXPIRES_SOON,
      hint: versionMarkExpiresHint(version.retentionMax),
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
  const when = formatVersionPickTime(version);
  const absolute = formatDateTime(version?.updatedAt || version?.createdAt, { style: 'absolute' });
  return [
    version?.id,
    version?.createdAt,
    version?.updatedAt,
    when,
    absolute,
    marks,
  ].filter(Boolean).join(' ');
}
