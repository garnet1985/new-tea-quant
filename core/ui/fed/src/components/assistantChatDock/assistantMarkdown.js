import React from 'react';
import PropTypes from 'prop-types';

function splitFences(text) {
  const source = String(text || '');
  const chunks = [];
  const fence = /```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g;
  let last = 0;
  let match = fence.exec(source);
  while (match) {
    if (match.index > last) {
      chunks.push({ type: 'md', text: source.slice(last, match.index) });
    }
    chunks.push({ type: 'code', lang: match[1] || '', text: match[2].replace(/\n$/, '') });
    last = match.index + match[0].length;
    match = fence.exec(source);
  }
  if (last < source.length) {
    chunks.push({ type: 'md', text: source.slice(last) });
  }
  return chunks;
}

function parseInline(text, keyPrefix) {
  const nodes = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let last = 0;
  let index = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const token = match[1];
    const key = `${keyPrefix}-${index}`;
    if (token.startsWith('`')) {
      nodes.push(<code key={key} className="ntq-assistant-md__code">{token.slice(1, -1)}</code>);
    } else {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    }
    index += 1;
    last = match.index + token.length;
    match = pattern.exec(text);
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function isTableRow(line) {
  return /^\s*\|.*\|\s*$/.test(line);
}

function isTableSep(line) {
  return /^\s*\|?\s*:?-{3,}/.test(line);
}

function splitCells(line) {
  const trimmed = line.trim();
  const inner = trimmed.startsWith('|') ? trimmed.slice(1) : trimmed;
  const withoutEnd = inner.endsWith('|') ? inner.slice(0, -1) : inner;
  return withoutEnd.split('|').map((cell) => cell.trim());
}

function nextNonEmpty(lines, start) {
  let i = start;
  while (i < lines.length && !String(lines[i]).trim()) i += 1;
  return i;
}

function collectListItems(lines, start, itemRe) {
  const items = [];
  let i = start;
  while (i < lines.length) {
    const j = nextNonEmpty(lines, i);
    if (j >= lines.length || !itemRe.test(lines[j])) break;
    let text = lines[j].replace(itemRe, '');
    i = j + 1;
    while (
      i < lines.length
      && lines[i].trim()
      && !itemRe.test(lines[i])
      && !/^\s*[-*]\s+/.test(lines[i])
      && !/^\s*\d+\.\s+/.test(lines[i])
      && !lines[i].startsWith('#')
      && !isTableRow(lines[i])
    ) {
      text += ` ${lines[i].trim()}`;
      i += 1;
    }
    items.push(text);
  }
  return { items, next: i };
}

function renderBlocks(text, keyPrefix) {
  const lines = String(text || '').replace(/\r\n/g, '\n').split('\n');
  const nodes = [];
  let i = 0;
  let block = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    const key = `${keyPrefix}-b${block}`;
    block += 1;

    if (isTableRow(line)) {
      const rows = [];
      while (i < lines.length && isTableRow(lines[i])) {
        if (!isTableSep(lines[i])) rows.push(splitCells(lines[i]));
        i += 1;
      }
      if (rows.length) {
        const header = rows[0];
        const body = rows.slice(1);
        nodes.push(
          <div key={key} className="ntq-assistant-md__table-wrap">
            <table className="ntq-assistant-md__table">
              <thead>
                <tr>
                  {header.map((cell, idx) => (
                    <th key={`${key}-h${idx}`}>{parseInline(cell, `${key}-h${idx}`)}</th>
                  ))}
                </tr>
              </thead>
              {body.length ? (
                <tbody>
                  {body.map((row, rIdx) => (
                    <tr key={`${key}-r${rIdx}`}>
                      {row.map((cell, cIdx) => (
                        <td key={`${key}-r${rIdx}c${cIdx}`}>{parseInline(cell, `${key}-r${rIdx}c${cIdx}`)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              ) : null}
            </table>
          </div>,
        );
      }
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const Tag = `h${level}`;
      nodes.push(
        <Tag key={key} className={`ntq-assistant-md__h ntq-assistant-md__h${level}`}>
          {parseInline(heading[2], key)}
        </Tag>,
      );
      i += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const collected = collectListItems(lines, i, /^\s*[-*]\s+/);
      i = collected.next;
      nodes.push(
        <ul key={key} className="ntq-assistant-md__list">
          {collected.items.map((item, idx) => (
            <li key={`${key}-${idx}`}>{parseInline(item, `${key}-${idx}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const collected = collectListItems(lines, i, /^\s*\d+\.\s+/);
      i = collected.next;
      nodes.push(
        <ol key={key} className="ntq-assistant-md__list ntq-assistant-md__list--ol">
          {collected.items.map((item, idx) => (
            <li key={`${key}-${idx}`}>{parseInline(item, `${key}-${idx}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    const para = [line];
    i += 1;
    while (
      i < lines.length
      && lines[i].trim()
      && !lines[i].startsWith('#')
      && !/^\s*[-*]\s+/.test(lines[i])
      && !/^\s*\d+\.\s+/.test(lines[i])
      && !isTableRow(lines[i])
    ) {
      para.push(lines[i]);
      i += 1;
    }
    nodes.push(
      <p key={key} className="ntq-assistant-md__p">
        {parseInline(para.join(' '), key)}
      </p>,
    );
  }
  return nodes;
}

function AssistantMarkdown({ text }) {
  const chunks = splitFences(text);
  return (
    <div className="ntq-assistant-md">
      {chunks.map((chunk, index) => (
        chunk.type === 'code' ? (
          <pre key={`c${index}`} className="ntq-assistant-md__pre">
            <code>{chunk.text}</code>
          </pre>
        ) : (
          <React.Fragment key={`m${index}`}>
            {renderBlocks(chunk.text, `m${index}`)}
          </React.Fragment>
        )
      ))}
    </div>
  );
}

AssistantMarkdown.propTypes = {
  text: PropTypes.string,
};

AssistantMarkdown.defaultProps = {
  text: '',
};

export default AssistantMarkdown;
