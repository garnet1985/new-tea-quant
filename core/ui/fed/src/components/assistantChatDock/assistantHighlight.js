import hljs from 'vendor/highlight';
import 'vendor/highlight/atom-one-dark.min.css';

const LANG_ALIAS = {
  py: 'python',
  python3: 'python',
  yml: 'yaml',
  sh: 'bash',
  shell: 'bash',
  js: 'javascript',
};

function resolveLanguage(lang) {
  const raw = String(lang || '').trim().toLowerCase();
  if (!raw) return '';
  const mapped = LANG_ALIAS[raw] || raw;
  return hljs.getLanguage(mapped) ? mapped : '';
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function highlightFence(text, lang) {
  const source = String(text || '');
  const language = resolveLanguage(lang);
  try {
    if (language) {
      return hljs.highlight(source, { language, ignoreIllegals: true }).value;
    }
    return hljs.highlightAuto(source).value;
  } catch {
    return escapeHtml(source);
  }
}
