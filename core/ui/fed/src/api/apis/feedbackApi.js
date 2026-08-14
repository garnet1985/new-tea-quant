import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_SETTINGS_FEEDBACK = `${API_VERSION_PREFIX}/settings/feedback`;
const API_FEEDBACK = `${API_VERSION_PREFIX}/feedback`;
const API_FEEDBACK_TASK_SUCCESS = `${API_VERSION_PREFIX}/feedback/task-success`;
const API_FEEDBACK_PROMPT = `${API_VERSION_PREFIX}/feedback/prompt`;

/**
 * @returns {Promise<{ prompts_disabled: boolean, decided_at: string, source: string, contact_url: string }>}
 */
export async function fetchFeedbackSettings() {
  const json = await requestJson(API_SETTINGS_FEEDBACK, { method: 'GET' });
  const m = json?.message || {};
  return {
    prompts_disabled: Boolean(m.prompts_disabled),
    decided_at: String(m.decided_at || '').trim(),
    source: String(m.source || '').trim(),
    contact_url: String(m.contact_url || 'https://new-tea.cn/zh-hans/contact?from=ntq_app').trim(),
  };
}

/**
 * @param {{ prompts_disabled: boolean, source?: string }} body
 */
export async function saveFeedbackSettings(body) {
  const source = String(body?.source || 'settings_ui').trim().slice(0, 32) || 'settings_ui';
  const json = await requestJson(API_SETTINGS_FEEDBACK, {
    method: 'POST',
    body: JSON.stringify({
      prompts_disabled: Boolean(body?.prompts_disabled),
      source,
    }),
  });
  const m = json?.message || {};
  return {
    prompts_disabled: Boolean(m.prompts_disabled),
    decided_at: String(m.decided_at || '').trim(),
    source: String(m.source || '').trim(),
    contact_url: String(m.contact_url || '').trim(),
  };
}

/**
 * @param {string} source
 * @returns {Promise<{ should_prompt: boolean, reason?: string }>}
 */
export async function noteFeedbackTaskSuccess(source) {
  const json = await requestJson(API_FEEDBACK_TASK_SUCCESS, {
    method: 'POST',
    body: JSON.stringify({ source: String(source || '').trim().slice(0, 32) }),
  });
  const m = json?.message || {};
  return {
    should_prompt: Boolean(m.should_prompt),
    reason: String(m.reason || '').trim(),
  };
}

/**
 * @param {{ rating: 'up'|'down', text?: string, source?: string }} body
 */
export async function submitFeedback(body) {
  const json = await requestJson(API_FEEDBACK, {
    method: 'POST',
    body: JSON.stringify({
      rating: String(body?.rating || '').trim().toLowerCase(),
      text: String(body?.text || ''),
      source: String(body?.source || 'popup').trim().slice(0, 32) || 'popup',
    }),
  });
  const m = json?.message || {};
  return { status: String(m.status || 'ok') };
}

/**
 * @param {{ action: 'snooze'|'disable', source?: string }} body
 */
export async function feedbackPromptAction(body) {
  const json = await requestJson(API_FEEDBACK_PROMPT, {
    method: 'POST',
    body: JSON.stringify({
      action: String(body?.action || '').trim().toLowerCase(),
      source: String(body?.source || 'popup').trim().slice(0, 32) || 'popup',
    }),
  });
  const m = json?.message || {};
  return { status: String(m.status || 'ok'), action: String(m.action || '') };
}
