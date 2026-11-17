import { MESSAGE_STATUSES } from 'ui/tokens';

const listeners = new Set();
let nextId = 0;

/**
 * 弹出右下角 Toast。需在应用壳挂载一次 ToastHost。
 *
 * @param {{ status?: string, severity?: string, content?: import('react').ReactNode, duration?: number }} [options]
 * `severity` 为旧 containers/toast API，等价于 `status`。
 */
export function showToast({ status, severity, content, duration = 2800 } = {}) {
  const text = content == null ? '' : content;
  if (text === '' || (typeof text === 'string' && !text.trim())) return;

  const resolved = status != null ? status : (severity != null ? severity : 'info');
  const item = {
    id: nextId + 1,
    status: MESSAGE_STATUSES.includes(resolved) ? resolved : 'info',
    content: text,
    duration: typeof duration === 'number' && duration > 0 ? duration : 2800,
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
