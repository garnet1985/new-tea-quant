const SEVERITIES = new Set(['info', 'success', 'warning', 'error']);
const listeners = new Set();
let nextId = 0;

export function showToast({ severity = 'info', content, duration = 2800 } = {}) {
  const text = content == null ? '' : content;
  if (text === '' || (typeof text === 'string' && !text.trim())) return;
  const item = {
    id: nextId + 1,
    severity: SEVERITIES.has(severity) ? severity : 'info',
    content: text,
    duration,
  };
  nextId = item.id;
  listeners.forEach((fn) => {
    fn(item);
  });
}

export function subscribeToast(fn) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
