import { formatDateTime, formatVersionPickTime } from '../../service/utils/formatDateTime';

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
    ? `系统目前最多保留 ${n} 组过时回测环境。`
    : '系统只保留有限组数的过时回测环境。';
  return [
    '不是按日历过期，也不是按单个 version 号抽。',
    capText,
    '当前环境整组保留。过时环境累计到上限后再出现新环境时，最旧的那一组会先被删掉。',
    'simulate 和战役结束时会自动清理。调整保留组数请到设置 → 数据范围。',
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
  if (Number.isFinite(n) && n > 0) return `当前设置最多保留 「${n}」组过时环境`;
  return '当前设置按组保留过时环境';
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
