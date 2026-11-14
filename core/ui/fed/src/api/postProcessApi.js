import request, { API_VERSION_PREFIX } from 'service/request';

const API_ADAPTERS = `${API_VERSION_PREFIX}/post-process/adapters`;
const API_PROCESSORS = `${API_VERSION_PREFIX}/post-process/processors`;

function mapReadiness(raw) {
  const r = raw && typeof raw === 'object' ? raw : {};
  return {
    ok: Boolean(r.ok),
    message: String(r.message || ''),
    missing: Array.isArray(r.missing) ? r.missing.map(String) : [],
  };
}

function mapAdapter(item) {
  const name = String(item?.name || '');
  return {
    id: name,
    name,
    display_name: String(item?.display_name || name).trim() || name,
    validate_ok: Boolean(item?.validate?.ok),
    validate_message: String(item?.validate?.message || ''),
    supports_dry_run: Boolean(item?.supports_dry_run),
    default_dry_run:
      item?.default_dry_run === null || item?.default_dry_run === undefined
        ? null
        : Boolean(item.default_dry_run),
    readiness: mapReadiness(item?.readiness),
    status: String(item?.status || 'unavailable'),
    remark: String(item?.remark || ''),
  };
}

function mapStep(row) {
  const name = String(row?.name || '');
  return {
    name,
    display_name: String(row?.display_name || name).trim() || name,
    depends_on: Array.isArray(row?.depends_on) ? row.depends_on.map(String) : [],
    dry_run:
      row?.dry_run === null || row?.dry_run === undefined
        ? null
        : Boolean(row.dry_run),
    validate_ok: Boolean(row?.validate?.ok),
    validate_message: String(row?.validate?.message || ''),
    readiness: mapReadiness(row?.readiness),
    supports_dry_run: Boolean(row?.supports_dry_run),
    status: String(row?.status || 'unavailable'),
    remark: String(row?.remark || ''),
  };
}

function mapProcessor(item) {
  const adapters = Array.isArray(item?.adapters) ? item.adapters : [];
  return {
    id: String(item?.key || ''),
    key: String(item?.key || ''),
    name: String(item?.name || item?.key || ''),
    is_enabled: Boolean(item?.is_enabled),
    on_error: String(item?.on_error || 'continue'),
    on_empty: String(item?.on_empty || 'run'),
    adapters: adapters.map(mapStep),
    execution_order: Array.isArray(item?.execution_order)
      ? item.execution_order.map(String)
      : [],
    order_error: String(item?.order_error || ''),
    validate_ok: Boolean(item?.validate?.ok),
    validate_message: String(item?.validate?.message || ''),
  };
}

/** GET /v1/post-process/adapters */
export async function fetchPostProcessAdapters() {
  const json = await request.getJson(API_ADAPTERS);
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  return {
    data: items.map(mapAdapter),
    total: Number(m.total ?? items.length) || 0,
  };
}

/** GET /v1/post-process/processors */
export async function fetchPostProcessProcessors() {
  const json = await request.getJson(API_PROCESSORS);
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  return {
    data: items.map(mapProcessor),
    total: Number(m.total ?? items.length) || 0,
  };
}

/** POST /v1/post-process/processors/<key>/enabled */
export async function setPostProcessEnabled(key, enabled) {
  const encoded = encodeURIComponent(String(key || '').trim());
  const json = await request.postJson(`${API_PROCESSORS}/${encoded}/enabled`, {
    body: { enabled: Boolean(enabled) },
  });
  return mapProcessor(json?.message?.item || {});
}

/**
 * PUT /v1/post-process/processors/<key>/adapters
 * @param {string} key
 * @param {Record<string, { depends_on?: string[] }>} adapters
 */
export async function updatePostProcessAdapters(key, adapters) {
  const encoded = encodeURIComponent(String(key || '').trim());
  const json = await request.putJson(`${API_PROCESSORS}/${encoded}/adapters`, {
    body: { adapters: adapters || {} },
  });
  return mapProcessor(json?.message?.item || {});
}

export function getAdapterDisplayLabel(rowOrName, adaptersByName) {
  if (rowOrName && typeof rowOrName === 'object') {
    return String(rowOrName.display_name || rowOrName.name || '').trim() || '—';
  }
  const name = String(rowOrName || '').trim();
  if (!name) return '—';
  const hit = adaptersByName?.[name];
  return String(hit?.display_name || name).trim() || name;
}

/** live | dry_run | unavailable */
export function getAdapterStatus(row, adaptersByName) {
  if (row && typeof row === 'object' && row.status) {
    return String(row.status);
  }
  const name = typeof row === 'string' ? row : row?.name;
  const hit = adaptersByName?.[name];
  if (hit?.status) return String(hit.status);
  return 'unavailable';
}

export function getAdapterStatusLabel(status) {
  switch (String(status || '')) {
    case 'live':
      return '可用';
    case 'dry_run':
      return '测试模式';
    default:
      return '不可用';
  }
}

export function getAdapterRemark(row) {
  const text = String(row?.remark || '').trim();
  if (text) return text;
  switch (getAdapterStatus(row)) {
    case 'live':
      return '可以正常使用';
    case 'dry_run':
      return '当前是测试模式';
    default:
      return '缺少必要配置';
  }
}
