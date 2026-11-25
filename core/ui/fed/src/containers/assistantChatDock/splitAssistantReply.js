/**
 * 从助手回复中拆出「下一步」建议与免责段，正文去掉以免与 UI 块重复。
 *
 * 支持：
 * - [下一步] 单行或后接列表
 * - ## 下一步 / ### 下一步
 * - 文末固定免责（硬/软文案）
 */

const NEXT_STEP_RE = /(?:^|\n)(?:#{1,3}\s*)?\[?\s*下一步\s*\]?\s*[:：]?\s*(?:\n|$)/i;

/** 模型常贴的回复向免责（硬法 + 软法变体） */
const DISCLAIMER_LINE_RE = /^(?:以上仅为研究思路[\s\S]*?新茶不对结果负责[。.]?|新茶提供的仅仅是参考建议[\s\S]*?负责[哦喔]?[。.]?)\s*$/m;

const DISCLAIMER_INLINE_RE = /(?:^|\n+)\s*(?:以上仅为研究思路[\s\S]*?新茶不对结果负责[。.]?|新茶提供的仅仅是参考建议[\s\S]*?负责[哦喔]?[。.]?)\s*$/;

/**
 * UI 展示用的软免责（与模型原文解耦）。
 */
export const REPLY_DISCLAIMER =
  '新茶提供的仅仅是参考建议，无法为您的结果负责哦。';

/**
 * @param {string} raw
 * @returns {{ body: string, suggestions: string[], showDisclaimer: boolean }}
 */
export function splitAssistantReply(raw) {
  const text = String(raw || '');
  const match = NEXT_STEP_RE.exec(text);
  let body;
  let suggestions = [];

  if (!match || match.index == null) {
    body = text.trim();
  } else {
    body = text.slice(0, match.index).replace(/\s+$/, '');
    let tail = text.slice(match.index + match[0].length).trim();
    const discInTail = DISCLAIMER_INLINE_RE.exec(`\n${tail}`);
    if (discInTail) {
      const cut = discInTail.index > 0 ? discInTail.index - 1 : 0;
      const before = tail.slice(0, cut).trim();
      const disc = tail.slice(cut).trim();
      suggestions = linesToSuggestions(before);
      body = [body, disc].filter(Boolean).join('\n\n');
    } else {
      suggestions = linesToSuggestions(tail);
    }
  }

  const stripped = stripDisclaimer(body);
  return {
    body: stripped.body,
    suggestions,
    showDisclaimer: stripped.found || suggestions.length > 0,
  };
}

/**
 * @param {string} body
 * @returns {{ body: string, found: boolean }}
 */
export function stripDisclaimer(body) {
  let text = String(body || '').trim();
  let found = false;

  // 整段匹配文末
  const end = DISCLAIMER_INLINE_RE.exec(`\n${text}`);
  if (end) {
    found = true;
    const cut = end.index > 0 ? end.index - 1 : 0;
    text = text.slice(0, cut).trim();
  }

  // 「建议」块里夹着的免责行
  const lines = text.split('\n');
  const kept = [];
  for (const line of lines) {
    if (DISCLAIMER_LINE_RE.test(line.trim())) {
      found = true;
      continue;
    }
    kept.push(line);
  }
  text = kept.join('\n').replace(/\n{3,}/g, '\n\n').trim();

  // 空掉只剩标题的「建议」块
  text = text.replace(/(?:^|\n)(#{1,3}\s*建议\s*)\n+(?=(?:#{1,3}\s|\s*$))/g, '\n').trim();

  return { body: text, found };
}

/**
 * @param {string} tail
 * @returns {string[]}
 */
function linesToSuggestions(tail) {
  const raw = String(tail || '').trim();
  if (!raw) return [];

  const lines = raw.split(/\n+/).map((line) => (
    line
      .replace(/^[-*•]\s+/, '')
      .replace(/^\d+[.)、]\s+/, '')
      .trim()
  )).filter(Boolean);

  const out = [];
  for (const line of lines) {
    if (/^#{1,3}\s/.test(line) || /^\[.+\]$/.test(line)) break;
    if (/^以上仅为|^新茶提供的仅仅是参考/.test(line)) break;
    const cleaned = line.replace(/^["「]|["」]$/g, '').trim();
    if (cleaned.length < 2) continue;
    out.push(cleaned.slice(0, 160));
    if (out.length >= 2) break;
  }

  if (!out.length && raw.length >= 2 && !/^以上仅为|^新茶提供的仅仅是参考/.test(raw)) {
    const para = raw.split(/\n\n/)[0].trim().slice(0, 160);
    if (para) out.push(para);
  }
  return out;
}

export default splitAssistantReply;
