/**
 * 从助手回复中拆出「下一步」建议（最多 2 条），正文去掉该段以免与 chip 重复。
 *
 * 支持：
 * - [下一步] 单行或后接列表
 * - ## 下一步 / ### 下一步
 */

const NEXT_STEP_RE = /(?:^|\n)(?:#{1,3}\s*)?\[?\s*下一步\s*\]?\s*[:：]?\s*(?:\n|$)/i;

/**
 * @param {string} raw
 * @returns {{ body: string, suggestions: string[] }}
 */
export function splitAssistantReply(raw) {
  const text = String(raw || '');
  const match = NEXT_STEP_RE.exec(text);
  if (!match || match.index == null) {
    return { body: text.trim(), suggestions: [] };
  }

  const body = text.slice(0, match.index).replace(/\s+$/, '');
  let tail = text.slice(match.index + match[0].length).trim();
  // 免责若误落在下一步之后，仍留在正文侧（不进 chip）
  const discIdx = tail.search(/以上仅为研究思路/);
  if (discIdx > 0) {
    // 免责夹在中间时：chip 只用免责前；免责拼回 body
    const before = tail.slice(0, discIdx).trim();
    const disc = tail.slice(discIdx).trim();
    tail = before;
    const mergedBody = [body, disc].filter(Boolean).join('\n\n');
    return { body: mergedBody, suggestions: linesToSuggestions(tail) };
  }
  if (discIdx === 0) {
    return { body: [body, tail].filter(Boolean).join('\n\n'), suggestions: [] };
  }

  return { body: body.trim(), suggestions: linesToSuggestions(tail) };
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
    if (/^以上仅为/.test(line)) break;
    const cleaned = line.replace(/^["「]|["」]$/g, '').trim();
    if (cleaned.length < 2) continue;
    out.push(cleaned.slice(0, 160));
    if (out.length >= 2) break;
  }

  if (!out.length && raw.length >= 2 && !/^以上仅为/.test(raw)) {
    const para = raw.split(/\n\n/)[0].trim().slice(0, 160);
    if (para) out.push(para);
  }
  return out;
}

export default splitAssistantReply;
