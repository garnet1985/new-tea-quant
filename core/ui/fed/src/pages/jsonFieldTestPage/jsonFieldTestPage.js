import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Chip,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import JSON5 from 'json5';
import PythonDictInputPanel from 'components/pythonDictInputPanel';
import PageLayout from '../../components/pageLayout/pageLayout';

const defaultInput = JSON.stringify(
  {
    rsi_oversold_threshold: 20,
    risk: { stop_loss_pct: 0.1, take_profit_pct: 0.2 },
    flags: { use_sampling: false, verbose: true },
    symbol_pool: ['000001.SZ', '000002.SZ'],
  },
  null,
  2,
);

function generateLargeSample() {
  const obj = {};
  for (let i = 0; i < 1500; i += 1) {
    obj[`factor_${i}`] = {
      enabled: i % 2 === 0,
      threshold: i * 1.03,
      tags: [`t${i}`, `t${i + 1}`],
    };
  }
  return JSON.stringify(obj);
}

function countSummary(value) {
  let objects = 0;
  let arrays = 0;
  let leaves = 0;
  const walk = (v) => {
    if (v === null || typeof v !== 'object') {
      leaves += 1;
      return;
    }
    if (Array.isArray(v)) {
      arrays += 1;
      v.forEach(walk);
      return;
    }
    objects += 1;
    Object.values(v).forEach(walk);
  };
  walk(value);
  return { objects, arrays, leaves };
}

function tryParseJson(text) {
  const t0 = performance.now();
  const parsed = JSON.parse(text);
  const t1 = performance.now();
  const pretty = JSON.stringify(parsed, null, 2);
  const t2 = performance.now();
  return {
    parsed,
    parseMs: Number((t1 - t0).toFixed(2)),
    prettyMs: Number((t2 - t1).toFixed(2)),
    pretty,
  };
}

function stripHashComments(text) {
  let out = '';
  let inSingle = false;
  let inDouble = false;
  let escaped = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (escaped) {
      out += ch;
      escaped = false;
      continue;
    }
    if (ch === '\\') {
      out += ch;
      escaped = true;
      continue;
    }
    if (!inDouble && ch === '\'') {
      inSingle = !inSingle;
      out += ch;
      continue;
    }
    if (!inSingle && ch === '"') {
      inDouble = !inDouble;
      out += ch;
      continue;
    }
    if (!inSingle && !inDouble && ch === '#') {
      while (i < text.length && text[i] !== '\n') i += 1;
      if (i < text.length) out += '\n';
      continue;
    }
    out += ch;
  }
  return out;
}

function replacePythonLiterals(text) {
  let out = '';
  let inSingle = false;
  let inDouble = false;
  let escaped = false;
  let token = '';

  const flushToken = () => {
    if (!token) return;
    if (token === 'True') out += 'true';
    else if (token === 'False') out += 'false';
    else if (token === 'None') out += 'null';
    else out += token;
    token = '';
  };

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (escaped) {
      flushToken();
      out += ch;
      escaped = false;
      continue;
    }
    if (ch === '\\') {
      flushToken();
      out += ch;
      escaped = true;
      continue;
    }
    if (!inDouble && ch === '\'') {
      flushToken();
      inSingle = !inSingle;
      out += ch;
      continue;
    }
    if (!inSingle && ch === '"') {
      flushToken();
      inDouble = !inDouble;
      out += ch;
      continue;
    }
    if (!inSingle && !inDouble && /[A-Za-z_]/.test(ch)) {
      token += ch;
      continue;
    }
    flushToken();
    out += ch;
  }
  flushToken();
  return out;
}

function tryParsePythonDictLike(text) {
  const t0 = performance.now();
  const noComments = stripHashComments(text);
  const normalized = replacePythonLiterals(noComments);
  const parsed = JSON5.parse(normalized);
  const t1 = performance.now();
  const pretty = JSON.stringify(parsed, null, 2);
  const t2 = performance.now();
  return {
    parsed,
    parseMs: Number((t1 - t0).toFixed(2)),
    prettyMs: Number((t2 - t1).toFixed(2)),
    pretty,
    mode: 'python-dict-like',
  };
}

function extractLineHint(errMsg) {
  const m = String(errMsg).match(/position\s+(\d+)/i);
  if (!m) return '';
  return `错误大致在第 ${m[1]} 个字符附近。`;
}

function extractErrorPosition(errMsg) {
  const m = String(errMsg).match(/position\s+(\d+)/i);
  if (!m) return -1;
  const pos = Number(m[1]);
  return Number.isNaN(pos) ? -1 : pos;
}

function extractErrorLineColumn(errMsg) {
  // 兼容 JSON5 常见格式："... at 12:34"
  const m1 = String(errMsg).match(/\bat\s+(\d+)\s*:\s*(\d+)\b/i);
  if (m1) {
    const line = Number(m1[1]);
    const column = Number(m1[2]);
    if (!Number.isNaN(line) && !Number.isNaN(column)) return { line, column };
  }
  // 兼容通用格式："line 12 column 34"
  const m2 = String(errMsg).match(/line\s+(\d+)\D+column\s+(\d+)/i);
  if (m2) {
    const line = Number(m2[1]);
    const column = Number(m2[2]);
    if (!Number.isNaN(line) && !Number.isNaN(column)) return { line, column };
  }
  return { line: 0, column: 0 };
}

function getLineColumnByPosition(text, position) {
  if (position < 0) return { line: 0, column: 0 };
  const lines = text.split('\n');
  let cursor = 0;
  for (let i = 0; i < lines.length; i += 1) {
    const lineLen = lines[i].length;
    if (position <= cursor + lineLen) {
      return { line: i + 1, column: position - cursor + 1 };
    }
    cursor += lineLen + 1;
  }
  return { line: lines.length, column: lines[lines.length - 1].length + 1 };
}

function getPositionByLineColumn(text, line, column) {
  if (line <= 0 || column <= 0) return -1;
  const lines = text.split('\n');
  let pos = 0;
  for (let i = 0; i < lines.length; i += 1) {
    const lineNo = i + 1;
    if (lineNo === line) {
      return pos + Math.max(0, Math.min(column - 1, lines[i].length));
    }
    pos += lines[i].length + 1;
  }
  return -1;
}

function getErrorContextLines(text, line, radius = 2) {
  if (!line) return [];
  const lines = text.split('\n');
  const start = Math.max(1, line - radius);
  const end = Math.min(lines.length, line + radius);
  const out = [];
  for (let ln = start; ln <= end; ln += 1) {
    out.push({ lineNo: ln, text: lines[ln - 1], isError: ln === line });
  }
  return out;
}

function convertPythonLikeToJson(text) {
  // 轻量转换，仅用于实验：True/False/None -> true/false/null
  // 单引号替换存在边界问题，因此不自动替换引号，避免误伤。
  return text
    .replace(/\bTrue\b/g, 'true')
    .replace(/\bFalse\b/g, 'false')
    .replace(/\bNone\b/g, 'null');
}

function JsonFieldTestPage() {
  const inputRef = useRef(null);
  const [jsonInput, setJsonInput] = useState(defaultInput);
  const [parseError, setParseError] = useState('');
  const [lineHint, setLineHint] = useState('');
  const [errorLine, setErrorLine] = useState(0);
  const [errorColumn, setErrorColumn] = useState(0);
  const [errorPosition, setErrorPosition] = useState(-1);
  const [metrics, setMetrics] = useState({
    parseMs: 0,
    prettyMs: 0,
    bytes: 0,
    objects: 0,
    arrays: 0,
    leaves: 0,
  });
  const [parsedPreview, setParsedPreview] = useState('');
  const [validated, setValidated] = useState(false);
  const [parseMode, setParseMode] = useState('未解析');

  const accuracyStatus = useMemo(
    () => (validated && !parseError ? '通过' : validated ? '失败' : '未验证'),
    [validated, parseError],
  );

  const validateJson = () => {
    try {
      let result;
      try {
        result = { ...tryParseJson(jsonInput), mode: 'json' };
      } catch (_jsonErr) {
        result = tryParsePythonDictLike(jsonInput);
      }
      const summary = countSummary(result.parsed);
      // 每次验证成功后统一格式化，确保用户输入被修复为标准 JSON 结构
      setJsonInput(result.pretty);
      setParseError('');
      setLineHint('');
      setErrorLine(0);
      setErrorColumn(0);
      setErrorPosition(-1);
      setValidated(true);
      setParseMode(result.mode === 'json' ? 'JSON' : 'Python dict 兼容');
      setParsedPreview(result.pretty);
      setMetrics({
        parseMs: result.parseMs,
        prettyMs: result.prettyMs,
        bytes: new Blob([jsonInput]).size,
        objects: summary.objects,
        arrays: summary.arrays,
        leaves: summary.leaves,
      });
    } catch (err) {
      const msg = err?.message || 'JSON 解析失败';
      let pos = extractErrorPosition(msg);
      let loc = getLineColumnByPosition(jsonInput, pos);
      if (loc.line <= 0 || loc.column <= 0) {
        const lc = extractErrorLineColumn(msg);
        if (lc.line > 0 && lc.column > 0) {
          loc = lc;
          pos = getPositionByLineColumn(jsonInput, lc.line, lc.column);
        }
      }
      setValidated(true);
      setParseError(msg);
      setParseMode('解析失败');
      setLineHint(extractLineHint(msg));
      setErrorLine(loc.line);
      setErrorColumn(loc.column);
      setErrorPosition(pos);
      setParsedPreview('');
      setMetrics((prev) => ({ ...prev, parseMs: 0, prettyMs: 0 }));
    }
  };

  const errorContext = useMemo(
    () => getErrorContextLines(jsonInput, errorLine, 2),
    [jsonInput, errorLine],
  );

  useEffect(() => {
    if (errorPosition < 0 || !inputRef.current) return;
    const textarea = inputRef.current;
    const pos = Math.max(0, Math.min(errorPosition, jsonInput.length));
    textarea.focus();
    textarea.setSelectionRange(pos, Math.min(pos + 1, jsonInput.length));
    const lineNo = jsonInput.slice(0, pos).split('\n').length;
    const lineHeight = 24;
    textarea.scrollTop = Math.max(0, (lineNo - 2) * lineHeight);
  }, [errorPosition, jsonInput]);

  return (
    <PageLayout
      className="json-field-test-page"
      breadcrumbsItems={[{ label: '策略实验室', to: '/strategy-workbench' }]}
      breadcrumbsCurrent="Raw JSON 测试"
      bannerTitle="Raw JSON 测试"
      bannerDescription="第一版不做字段树渲染，只验证输入体验、错误提示友好性和性能表现。"
    >

      {parseError ? (
        <Typography variant="caption" color="error" sx={{ display: 'block', mb: 1 }}>
          输入区上方已显示错误信息与定位，请先修复后再应用。
        </Typography>
      ) : null}

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="stretch">
        <PythonDictInputPanel
          inputRef={inputRef}
          value={jsonInput}
          onChange={(nextText) => {
            setJsonInput(nextText);
            setValidated(false);
          }}
          onApply={validateJson}
          onLoadDefault={() => {
            setJsonInput(defaultInput);
            setValidated(false);
          }}
          onLoadLarge={() => {
            setJsonInput(generateLargeSample());
            setValidated(false);
          }}
          onConvertPythonLiteral={() => {
            setJsonInput((prev) => convertPythonLikeToJson(prev));
            setValidated(false);
          }}
          parseError={parseError}
          lineHint={lineHint}
          errorLine={errorLine}
          errorColumn={errorColumn}
          errorContext={errorContext}
        />

        <Paper variant="outlined" sx={{ p: 2, flex: 1.35, minWidth: 0 }}>
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
            右栏：验证结果与性能
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1.5 }}>
            <Chip
              color={accuracyStatus === '通过' ? 'success' : accuracyStatus === '失败' ? 'error' : 'default'}
              label={`准确性: ${accuracyStatus}`}
              size="small"
            />
            <Chip label={`模式: ${parseMode}`} size="small" />
            <Chip label={`parse: ${metrics.parseMs}ms`} size="small" />
            <Chip label={`pretty: ${metrics.prettyMs}ms`} size="small" />
            <Chip label={`bytes: ${metrics.bytes}`} size="small" />
            <Chip label={`objects: ${metrics.objects}`} size="small" />
            <Chip label={`arrays: ${metrics.arrays}`} size="small" />
            <Chip label={`leaves: ${metrics.leaves}`} size="small" />
          </Stack>

          <Alert severity="warning" sx={{ mb: 1.5 }}>
            可操作性评估标准（第一版）：能快速粘贴、看懂错误、修正后一次通过。
          </Alert>

          <Divider sx={{ mb: 1.5 }} />
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
            标准化输出（通过后）
          </Typography>
          <TextField
            multiline
            minRows={14}
            value={parsedPreview}
            fullWidth
            placeholder="验证通过后，这里显示格式化 JSON"
            InputProps={{ readOnly: true }}
          />
        </Paper>
      </Stack>
    </PageLayout>
  );
}

export default JsonFieldTestPage;
