import React from 'react';

/**
 * 把文案里的「专有名词」渲成高亮。
 * 约定：用中文书名号 「…」包起来；无匹配则原样返回。
 */
export function renderHelpRichText(text) {
  if (text == null || text === false) return null;
  if (typeof text !== 'string') return text;

  const parts = [];
  const re = /「([^」]+)」/g;
  let last = 0;
  let match;
  let key = 0;

  while ((match = re.exec(text))) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    parts.push(
      <span key={`term-${key}`} className="ntq-global-helper__term">
        {`「${match[1]}」`}
      </span>,
    );
    key += 1;
    last = match.index + match[0].length;
  }

  if (key === 0) return text;

  if (last < text.length) {
    parts.push(text.slice(last));
  }

  return parts;
}
