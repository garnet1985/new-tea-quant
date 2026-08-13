import { noteFeedbackTaskSuccess } from '../api/apis/feedbackApi';

const listeners = new Set();

/**
 * Subscribe to soft-feedback prompt requests.
 * @param {(payload: { source: string }) => void} fn
 * @returns {() => void}
 */
export function subscribeFeedbackPrompt(fn) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

function emitFeedbackPrompt(payload) {
  listeners.forEach((fn) => {
    try {
      fn(payload);
    } catch {
      // ignore listener errors
    }
  });
}

/**
 * Call after a successful user task. May open the soft feedback prompt.
 * @param {string} source
 */
export async function notifyTaskSuccess(source) {
  try {
    const r = await noteFeedbackTaskSuccess(source);
    if (r?.should_prompt) {
      emitFeedbackPrompt({ source: String(source || '').trim() || 'task' });
    }
  } catch {
    // never block task UX
  }
}
