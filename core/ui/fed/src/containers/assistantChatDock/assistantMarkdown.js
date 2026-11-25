import React from 'react';
import PropTypes from 'prop-types';
import { highlightFence } from './assistantHighlight';

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
    const lang = String(match[1] || '').toLowerCase();
    const body = match[2].replace(/\n$/, '');
    if (lang === 'metrics' || lang === 'kpi') {
      chunks.push({ type: 'metrics', text: body });
    } else {
      chunks.push({ type: 'code', lang: match[1] || '', text: body });
    }
    last = match.index + match[0].length;
    match = fence.exec(source);
  }
  if (last < source.length) {
    chunks.push({ type: 'md', text: source.slice(last) });
  }
  return chunks;
}

function toneForUnsignedPercent(before) {
  const ctx = String(before || '').slice(-28);
  if (/回撤|亏损|止损|跌幅|回落|回吐|回撤期/.test(ctx)) return 'neg';
  if (/收益|胜率|年化|夏普|索提诺|卡玛|完成率|利用率|盈利|回报|触发率/.test(ctx)) {
    return 'pos';
  }
  return '';
}

/**
 * Highlight signed metrics (+4.31% / -13%) and context-aware bare percents.
 */
function colorizeMetrics(text, keyPrefix) {
  const source = String(text || '');
  if (!source) return [];
  const nodes = [];
  const re = /(?<![\d])([+-])(\d+(?:\.\d+)?)(%)?(?![\d-])|(?<![+\-\d.])(\d+(?:\.\d+)?)(%)(?![\d%])/g;
  let last = 0;
  let index = 0;
  let match = re.exec(source);
  while (match) {
    if (match.index > last) {
      nodes.push(source.slice(last, match.index));
    }
    const key = `${keyPrefix}-n${index}`;
    index += 1;
    let tone = '';
    let token = match[0];
    if (match[1]) {
      tone = match[1] === '+' ? 'pos' : 'neg';
      token = `${match[1]}${match[2]}${match[3] || ''}`;
    } else {
      tone = toneForUnsignedPercent(source.slice(0, match.index));
      token = `${match[4]}${match[5]}`;
    }
    if (tone) {
      nodes.push(
        <span key={key} className={`ntq-assistant-md__num ntq-assistant-md__num--${tone}`}>
          {token}
        </span>,
      );
    } else {
      nodes.push(token);
    }
    last = match.index + match[0].length;
    match = re.exec(source);
  }
  if (last < source.length) nodes.push(source.slice(last));
  return nodes;
}

function parseInline(text, keyPrefix) {
  const nodes = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let last = 0;
  let index = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > last) {
      nodes.push(...colorizeMetrics(text.slice(last, match.index), `${keyPrefix}-t${index}`));
    }
    const token = match[1];
    const key = `${keyPrefix}-${index}`;
    if (token.startsWith('`')) {
      nodes.push(<code key={key} className="ntq-assistant-md__code">{token.slice(1, -1)}</code>);
    } else {
      nodes.push(
        <strong key={key}>
          {colorizeMetrics(token.slice(2, -2), `${key}-b`)}
        </strong>,
      );
    }
    index += 1;
    last = match.index + token.length;
    match = pattern.exec(text);
  }
  if (last < text.length) {
    nodes.push(...colorizeMetrics(text.slice(last), `${keyPrefix}-t${index}`));
  }
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

/**
 * 模型常把长「结论」写成列表最后一项；拆成段落后再渲染。
 */
function peelTrailingSummary(items) {
  if (!Array.isArray(items) || items.length < 2) {
    return { items, summary: null };
  }
  const last = String(items[items.length - 1] || '').trim();
  if (!last) return { items, summary: null };
  const others = items.slice(0, -1);
  const avg = others.reduce((sum, text) => sum + String(text).length, 0) / others.length;
  const summaryLead = /^(结论|综合来看|综合判断|总结|因此|所以|简言之|总的来说|总体来看|综上)/;
  const looksSummary = summaryLead.test(last) && last.length >= 40;
  const looksLongTail = last.length >= 90 && last.length >= avg * 2.2;
  if (looksSummary || looksLongTail) {
    return { items: others, summary: last };
  }
  return { items, summary: null };
}

function headingLayerClass(title) {
  const text = String(title || '').replace(/\*+/g, '');
  if (/枚举|机会盘点/.test(text)) return 'ntq-assistant-md__h--layer-enum';
  if (/价格/.test(text)) return 'ntq-assistant-md__h--layer-price';
  if (/资金/.test(text)) return 'ntq-assistant-md__h--layer-capital';
  if (/归因|止盈止损对照|止盈止损/.test(text)) return 'ntq-assistant-md__h--layer-attr';
  if (/滚动|多时段/.test(text)) return 'ntq-assistant-md__h--layer-roll';
  if (/特征标签|标签计算/.test(text)) return 'ntq-assistant-md__h--layer-tag';
  if (/测试计划|资金模拟计划|特征标签计划/.test(text)) return 'ntq-assistant-md__h--layer-plan';
  if (/建议|下一步/.test(text)) return 'ntq-assistant-md__h--layer-advice';
  return '';
}

function sectionToneClass(title) {
  const layer = headingLayerClass(title);
  if (!layer) return '';
  return layer.replace('__h--layer-', '__section--');
}

/** `**胜率**：55%` / `胜率：55%（偏高）` → metric card fields */
function parseMetricItem(raw) {
  const text = String(raw || '').trim();
  const match = text.match(/^\*{0,2}([^*\n：:]{1,24})\*{0,2}\s*[：:]\s*(.+)$/);
  if (!match) return null;
  const title = match[1].trim();
  let rest = match[2].trim();
  if (!title || !rest || rest.length > 48) return null;
  let hint = '';
  const hintMatch = rest.match(/^(.+?)\s*[（(]([^）)]{1,24})[）)]\s*$/);
  if (hintMatch) {
    rest = hintMatch[1].trim();
    hint = hintMatch[2].trim();
  }
  if (!rest || /[。；;\n]/.test(rest)) return null;
  return { title, value: rest, hint };
}

function tryMetricCards(items) {
  if (!Array.isArray(items) || items.length < 2 || items.length > 8) return null;
  const cards = items.map(parseMetricItem);
  if (cards.some((card) => !card)) return null;
  return cards;
}

function renderMetricGrid(key, cards) {
  return (
    <div key={key} className="ntq-assistant-md__metrics">
      {cards.map((card, idx) => (
        <div key={`${key}-m${idx}`} className="ntq-assistant-md__metric">
          <div className="ntq-assistant-md__metric-title">{card.title}</div>
          <div className="ntq-assistant-md__metric-value">
            {parseInline(card.value, `${key}-m${idx}-v`)}
          </div>
          {card.hint ? (
            <div className="ntq-assistant-md__metric-hint">{card.hint}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function parseMetricsFence(text) {
  const cards = [];
  String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      if (line.includes('|')) {
        const parts = line.split('|').map((part) => part.trim()).filter(Boolean);
        if (parts.length >= 2) {
          cards.push({
            title: parts[0],
            value: parts[1],
            hint: parts[2] || '',
          });
          return;
        }
      }
      const parsed = parseMetricItem(line);
      if (parsed) cards.push(parsed);
    });
  return cards;
}

function pushListNodes(nodes, key, Tag, className, items) {
  const peeled = peelTrailingSummary(items);
  const metricCards = tryMetricCards(peeled.items);
  if (metricCards) {
    nodes.push(renderMetricGrid(key, metricCards));
  } else {
    nodes.push(
      <Tag key={key} className={className}>
        {peeled.items.map((item, idx) => (
          <li key={`${key}-${idx}`}>{parseInline(item, `${key}-${idx}`)}</li>
        ))}
      </Tag>,
    );
  }
  if (peeled.summary) {
    nodes.push(
      <p key={`${key}-summary`} className="ntq-assistant-md__p ntq-assistant-md__p--summary">
        {parseInline(peeled.summary, `${key}-summary`)}
      </p>,
    );
  }
}

/**
 * 模型常把「1. …；2. …」写在同一段里；拆成换行后才能渲染成 ol/li。
 */
function normalizeCompactLists(text) {
  let source = String(text || '').replace(/\r\n/g, '\n');
  const structured = source
    .split('\n')
    .filter((line) => /^\s*(\d+\.|[-*])\s+/.test(line));
  if (structured.length >= 2) {
    return source;
  }
  source = source.replace(/([：:])\s*(?=\d+\.\s)/g, '$1\n');
  source = source.replace(/[；;]\s*(?=\d+\.\s)/g, '\n');
  source = source.replace(/[；;]\s*(?=[-*]\s+)/g, '\n');
  return source;
}

function renderBlocks(text, keyPrefix) {
  const lines = normalizeCompactLists(text).split('\n');
  const nodes = [];
  let i = 0;
  let block = 0;
  let sectionNodes = null;
  let sectionKey = '';
  let sectionTitle = '';

  const flushSection = () => {
    if (!sectionNodes) return;
    const tone = sectionToneClass(sectionTitle);
    nodes.push(
      <section
        key={sectionKey}
        className={['ntq-assistant-md__section', tone].filter(Boolean).join(' ')}
      >
        {sectionNodes}
      </section>,
    );
    sectionNodes = null;
    sectionKey = '';
    sectionTitle = '';
  };

  const pushNode = (node, asSectionBody = false) => {
    if (sectionNodes && asSectionBody) {
      sectionNodes.push(node);
      return;
    }
    if (sectionNodes && !asSectionBody) {
      flushSection();
    }
    nodes.push(node);
  };

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    const key = `${keyPrefix}-b${block}`;
    block += 1;
    const inSection = Boolean(sectionNodes);

    if (isTableRow(line)) {
      const rows = [];
      while (i < lines.length && isTableRow(lines[i])) {
        if (!isTableSep(lines[i])) rows.push(splitCells(lines[i]));
        i += 1;
      }
      if (rows.length) {
        const header = rows[0];
        const body = rows.slice(1);
        pushNode(
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
          inSection,
        );
      }
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const Tag = `h${level}`;
      const title = heading[2];
      if (level === 1) {
        flushSection();
        pushNode(
          <Tag key={key} className="ntq-assistant-md__h ntq-assistant-md__h1">
            {parseInline(title, key)}
          </Tag>,
          false,
        );
        i += 1;
        continue;
      }
      if (level === 2) {
        flushSection();
        sectionKey = key;
        sectionTitle = title;
        const layer = headingLayerClass(title);
        sectionNodes = [
          <Tag
            key={`${key}-title`}
            className={['ntq-assistant-md__h', 'ntq-assistant-md__h2', layer].filter(Boolean).join(' ')}
          >
            {parseInline(title, key)}
          </Tag>,
        ];
        i += 1;
        continue;
      }
      pushNode(
        <Tag
          key={key}
          className={['ntq-assistant-md__h', `ntq-assistant-md__h${level}`].join(' ')}
        >
          {parseInline(title, key)}
        </Tag>,
        inSection,
      );
      i += 1;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quoteLines = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) {
        quoteLines.push(lines[i].replace(/^\s*>\s?/, ''));
        i += 1;
      }
      const quoteText = quoteLines.join(' ').trim();
      if (quoteText) {
        const isConclusion = /^结论[：:]/.test(quoteText);
        pushNode(
          <blockquote
            key={key}
            className={[
              'ntq-assistant-md__quote',
              isConclusion ? 'ntq-assistant-md__quote--conclusion' : '',
            ].filter(Boolean).join(' ')}
          >
            {parseInline(quoteText, key)}
          </blockquote>,
          inSection,
        );
      }
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const collected = collectListItems(lines, i, /^\s*[-*]\s+/);
      i = collected.next;
      const listNodes = [];
      pushListNodes(listNodes, key, 'ul', 'ntq-assistant-md__list', collected.items);
      listNodes.forEach((node) => pushNode(node, inSection));
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      const collected = collectListItems(lines, i, /^\s*\d+\.\s+/);
      i = collected.next;
      const listNodes = [];
      pushListNodes(
        listNodes,
        key,
        'ol',
        'ntq-assistant-md__list ntq-assistant-md__list--ol',
        collected.items,
      );
      listNodes.forEach((node) => pushNode(node, inSection));
      continue;
    }

    const para = [line];
    i += 1;
    while (
      i < lines.length
      && lines[i].trim()
      && !lines[i].startsWith('#')
      && !/^\s*>\s?/.test(lines[i])
      && !/^\s*[-*]\s+/.test(lines[i])
      && !/^\s*\d+\.\s+/.test(lines[i])
      && !isTableRow(lines[i])
    ) {
      para.push(lines[i]);
      i += 1;
    }
    pushNode(
      <p key={key} className="ntq-assistant-md__p">
        {parseInline(para.join(' '), key)}
      </p>,
      inSection,
    );
  }

  flushSection();
  return nodes;
}

function AssistantMarkdown({ text = '' }) {
  const chunks = splitFences(text);
  return (
    <div className="ntq-assistant-md">
      {chunks.map((chunk, index) => {
        if (chunk.type === 'metrics') {
          const cards = parseMetricsFence(chunk.text);
          if (!cards.length) return null;
          return renderMetricGrid(`metrics-${index}`, cards);
        }
        if (chunk.type === 'code') {
          return (
            <pre key={`c${index}`} className="ntq-assistant-md__pre">
              <code
                className={['hljs', chunk.lang ? `language-${chunk.lang}` : ''].filter(Boolean).join(' ')}
                dangerouslySetInnerHTML={{ __html: highlightFence(chunk.text, chunk.lang) }}
              />
            </pre>
          );
        }
        return (
          <React.Fragment key={`m${index}`}>
            {renderBlocks(chunk.text, `m${index}`)}
          </React.Fragment>
        );
      })}
    </div>
  );
}

AssistantMarkdown.propTypes = {
  text: PropTypes.string,
};

export default AssistantMarkdown;
