import React, { useMemo } from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { Box, Chip, Stack, Typography } from '@mui/material';
import { DICT_PARSER_TEXT_FONT } from 'components/editor/fields/dictParser';

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

const LEGEND_SX = { width: 10, height: 10, borderRadius: 0.5, flexShrink: 0 };

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
    <Stack spacing={1} sx={{ height: '100%', minHeight: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
        基于
        {' '}
        <Typography component="span" variant="caption" sx={{ fontFamily: 'monospace' }}>react-diff-viewer-continued</Typography>
        {' '}
        + 行级 diff；缩进 {JSON_INDENT} 空格；字体同 Dict 编辑器。
      </Typography>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ flexShrink: 0 }}>
        <Chip
          size="small"
          label={structuralDiffs === 0 ? '对象结构无差异' : `对象路径差异约 ${structuralDiffs} 处`}
          color={structuralDiffs === 0 ? 'default' : 'warning'}
          variant={structuralDiffs === 0 ? 'outlined' : 'filled'}
        />
        <Stack direction="row" spacing={1} alignItems="center">
          <Box sx={{ ...LEGEND_SX, bgcolor: 'rgba(211, 47, 47, 0.2)', border: 1, borderColor: 'error.light' }} />
          <Typography variant="caption" color="text.secondary">删除行（左）</Typography>
        </Stack>
        <Stack direction="row" spacing={1} alignItems="center">
          <Box sx={{ ...LEGEND_SX, bgcolor: 'rgba(46, 125, 50, 0.22)', border: 1, borderColor: 'success.light' }} />
          <Typography variant="caption" color="text.secondary">新增行（右）</Typography>
        </Stack>
      </Stack>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: 'grey.50',
          '& table': { borderCollapse: 'collapse' },
        }}
      >
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
      </Box>
    </Stack>
  );
}

export default SettingsJsonDiff;
