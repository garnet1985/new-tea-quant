import React, { useMemo } from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { Tag } from 'ui';
import { DICT_PARSER_TEXT_FONT } from 'containers/editor';
import './style.scss';

/** 与常见编辑器一致；过大缩进会加重横向滚动 */
const JSON_INDENT = 2;

export function buildSettingsDiff(left, right) {
  if (left === undefined && right === undefined) {
    return { type: 'equal', value: undefined };
  }
  if (left === undefined) {
    return { type: 'only_right', value: right };
  }
  if (right === undefined) {
    return { type: 'only_left', value: left };
  }
  if (Object.is(left, right)) {
    return { type: 'equal', value: left };
  }
  if (left === null || right === null) {
    return { type: 'diff', left, right };
  }
  const tl = typeof left;
  const tr = typeof right;
  if (tl !== tr || tl !== 'object') {
    return { type: 'diff', left, right };
  }
  if (Array.isArray(left) && Array.isArray(right)) {
    const n = Math.max(left.length, right.length);
    const items = [];
    for (let i = 0; i < n; i += 1) {
      items.push(buildSettingsDiff(left[i], right[i]));
    }
    return { type: 'array', items };
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    return { type: 'diff', left, right };
  }
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  const children = {};
  for (const key of [...keys].sort()) {
    children[key] = buildSettingsDiff(left[key], right[key]);
  }
  return { type: 'object', children };
}

export function countSettingsDiffs(node) {
  if (!node) return 0;
  switch (node.type) {
    case 'equal':
      return 0;
    case 'only_left':
    case 'only_right':
    case 'diff':
      return 1;
    case 'array':
      return node.items.reduce((sum, item) => sum + countSettingsDiffs(item), 0);
    case 'object':
      return Object.values(node.children).reduce((sum, ch) => sum + countSettingsDiffs(ch), 0);
    default:
      return 0;
  }
}

function formatSettingsJson(obj) {
  if (obj === undefined) return '';
  try {
    return JSON.stringify(obj, null, JSON_INDENT);
  } catch {
    return String(obj);
  }
}

/**
 * 使用 ``react-diff-viewer-continued``（底层 ``diff`` 库）做**行级**文本对比；
 * 展示前将 settings 格式化为 JSON（{JSON_INDENT} 空格缩进），与核心 Dict 编辑器等宽字体。
 */
function SettingsJsonDiff({
  left,
  right,
  leftTitle = '当前版本',
  rightTitle = '对比版本',
}) {
  const oldStr = useMemo(() => formatSettingsJson(left), [left]);
  const newStr = useMemo(() => formatSettingsJson(right), [right]);
  const structuralDiffs = useMemo(
    () => countSettingsDiffs(buildSettingsDiff(left, right)),
    [left, right],
  );

  return (
    <div className="ntq-settings-json-diff">
      <p className="ntq-settings-json-diff__meta ntq-muted">
        基于
        {' '}
        <code className="ntq-settings-json-diff__code">react-diff-viewer-continued</code>
        {' '}
        + 行级 diff；缩进 {JSON_INDENT} 空格；字体同 Dict 编辑器。
      </p>
      <div className="ntq-settings-json-diff__legend">
        <Tag
          status={structuralDiffs === 0 ? 'neutral' : 'warning'}
          variant={structuralDiffs === 0 ? 'outline' : 'solid'}
        >
          {structuralDiffs === 0 ? '对象结构无差异' : `对象路径差异约 ${structuralDiffs} 处`}
        </Tag>
        <span className="ntq-settings-json-diff__swatch-row">
          <span className="ntq-settings-json-diff__swatch ntq-settings-json-diff__swatch--removed" />
          <span className="ntq-caption ntq-muted">删除行（左）</span>
        </span>
        <span className="ntq-settings-json-diff__swatch-row">
          <span className="ntq-settings-json-diff__swatch ntq-settings-json-diff__swatch--added" />
          <span className="ntq-caption ntq-muted">新增行（右）</span>
        </span>
      </div>

      <div className="ntq-settings-json-diff__viewer">
        <ReactDiffViewer
          oldValue={oldStr}
          newValue={newStr}
          splitView
          leftTitle={leftTitle}
          rightTitle={rightTitle}
          compareMethod={DiffMethod.LINES}
          disableWordDiff
          showDiffOnly={false}
          useDarkTheme={false}
          styles={{
            variables: {
              light: {
                diffViewerBackground: '#fafafa',
                diffViewerTitleBackground: '#eceff1',
                diffViewerTitleColor: '#37474f',
                diffViewerTitleBorderColor: '#cfd8dc',
                addedBackground: 'rgba(46, 125, 50, 0.1)',
                removedBackground: 'rgba(211, 47, 47, 0.09)',
                gutterBackground: '#f5f5f5',
                highlightBackground: 'rgba(237, 108, 2, 0.08)',
              },
            },
            contentText: {
              ...DICT_PARSER_TEXT_FONT,
            },
            line: {
              ...DICT_PARSER_TEXT_FONT,
              verticalAlign: 'top',
            },
          }}
        />
      </div>
    </div>
  );
}

export default SettingsJsonDiff;
