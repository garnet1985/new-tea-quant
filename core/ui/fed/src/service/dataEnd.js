/** Map BFF ``data_end`` payload for list / freshness responses. */
export function mapDataEnd(dataEnd) {
  const raw = dataEnd && typeof dataEnd === 'object' ? dataEnd : {};
  return {
    configured_as_of: raw.configured_as_of ?? null,
    effective_end_date: raw.effective_end_date ?? null,
    is_end_date_truncated: Boolean(raw.is_end_date_truncated),
    truncation_hint: String(raw.truncation_hint || '').trim(),
    truncation_settings_path: String(raw.truncation_settings_path || '').trim() || null,
  };
}
