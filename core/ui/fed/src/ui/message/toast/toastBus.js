import { MESSAGE_STATUSES } from 'ui/tokens';

const listeners = new Set();
let nextId = 0;

/**
 * 弹出右下角 Toast。需在应用壳挂载一次 ToastHost。
 *
 * @param {{ status?: string, content?: import('react').ReactNode, duration?: number }} [options]
 */
export function showToast({ status = 'info', content, duration = 2800 } = {}) {
  const text = content == null ? '' : content;
  if (text === '' || (typeof text === 'string' && !text.trim())) return;

  const item = {
    id: nextId + 1,
    status: MESSAGE_STATUSES.includes(status) ? status : 'info',
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
