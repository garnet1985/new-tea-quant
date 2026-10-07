export function pickRememberedSession(listed) {
  const sessions = Array.isArray(listed?.sessions) ? listed.sessions : [];
  const last = String(listed?.lastSessionId || listed?.last_session_id || '').trim();
  const idOf = (row) => String(row?.dmId || row?.dm_id || '').trim();
  if (last && sessions.some((row) => idOf(row) === last)) return last;
  if (!sessions.length) return '';
  const sorted = [...sessions].sort((a, b) => (
    String(b.updatedAt || b.updated_at || '').localeCompare(
      String(a.updatedAt || a.updated_at || ''),
    )
  ));
  return idOf(sorted[0]);
}

export function unfinishedSessions(sessions) {
  return (sessions || []).filter((row) => row.status === 'in_progress');
}
