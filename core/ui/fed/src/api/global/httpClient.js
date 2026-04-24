export async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });
  const json = await response.json();
  if (!response.ok || json?.status !== 'ok') {
    throw new Error(json?.message?.detail || `HTTP ${response.status}`);
  }
  return json;
}
