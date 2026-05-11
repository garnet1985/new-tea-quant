import { useEffect, useMemo, useRef, useState } from 'react';
import JSON5 from 'json5';

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
  const noComments = stripHashComments(text);
  const normalized = replacePythonLiterals(noComments);
  const parsed = JSON5.parse(normalized);
  return {
    parsed,
    pretty: JSON.stringify(parsed, null, 2),
    mode: 'Python dict 兼容',
  };
}

function extractErrorPosition(errMsg) {
  const m = String(errMsg).match(/position\s+(\d+)/i);
  if (!m) return -1;
  const pos = Number(m[1]);
  return Number.isNaN(pos) ? -1 : pos;
}

function extractErrorLineColumn(errMsg) {
  const m1 = String(errMsg).match(/\bat\s+(\d+)\s*:\s*(\d+)\b/i);
  if (m1) {
    const line = Number(m1[1]);
    const column = Number(m1[2]);
    if (!Number.isNaN(line) && !Number.isNaN(column)) return { line, column };
  }
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
  return { line: lines.length, column: (lines[lines.length - 1] || '').length + 1 };
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

function StrategySettingsContainer({ initialSettings, children }) {
  const normalizedInitial = useMemo(() => initialSettings || {}, [initialSettings]);
  const [draftSettings, setDraftSettings] = useState(normalizedInitial);
  const coreValueText = useMemo(
    () => JSON.stringify(draftSettings?.core || {}, null, 2),
    [draftSettings?.core],
  );
  const [coreInputText, setCoreInputText] = useState(coreValueText);
  const [coreParseError, setCoreParseError] = useState('');
  const [coreLineHint, setCoreLineHint] = useState('');
  const [coreErrorLine, setCoreErrorLine] = useState(0);
  const [coreErrorColumn, setCoreErrorColumn] = useState(0);
  const [coreErrorPosition, setCoreErrorPosition] = useState(-1);
  const [coreParseMode, setCoreParseMode] = useState('');
  const coreInputRef = useRef(null);

  useEffect(() => {
    setDraftSettings(normalizedInitial);
  }, [normalizedInitial]);

  useEffect(() => {
    setCoreInputText(coreValueText);
  }, [coreValueText]);

  const updateSection = (sectionKey, nextSectionValue) => {
    setDraftSettings((prev) => ({
      ...prev,
      [sectionKey]: nextSectionValue,
    }));
  };

  const parseCoreInput = (text) => {
    let result;
    try {
      const parsed = JSON.parse(text);
      result = {
        parsed,
        pretty: JSON.stringify(parsed, null, 2),
        mode: 'JSON',
      };
    } catch (_jsonErr) {
      result = tryParsePythonDictLike(text);
    }
    if (!result?.parsed || typeof result.parsed !== 'object' || Array.isArray(result.parsed)) {
      throw new Error('core 必须是 dict/object');
    }
    return result;
  };

  const applyCoreSourceFailure = (text, err, focusOnError) => {
    const msg = err?.message || '解析失败';
    let pos = extractErrorPosition(msg);
    let loc = getLineColumnByPosition(text, pos);
    if (loc.line <= 0 || loc.column <= 0) {
      const lc = extractErrorLineColumn(msg);
      if (lc.line > 0 && lc.column > 0) {
        loc = lc;
        pos = getPositionByLineColumn(text, lc.line, lc.column);
      }
    }
    setCoreParseError(msg);
    setCoreLineHint(pos >= 0 ? `错误大致在第 ${pos} 个字符附近。` : '');
    setCoreErrorLine(loc.line);
    setCoreErrorColumn(loc.column);
    setCoreErrorPosition(focusOnError ? pos : -1);
    setCoreParseMode('');
  };

  /** 解析 ``text`` 并写入草稿；可选失焦时 pretty-print。keyup / blur / 粘贴后同步用 DOM 当前值，避免仅依赖闭包里的 ``coreInputText``。 */
  const applyCoreSourceText = (
    text,
    { formatOnSuccess = false, focusOnError = false } = {},
  ) => {
    try {
      const result = parseCoreInput(text);
      if (formatOnSuccess) setCoreInputText(result.pretty);
      setDraftSettings((prev) => ({ ...prev, core: result.parsed }));
      setCoreParseError('');
      setCoreLineHint('');
      setCoreErrorLine(0);
      setCoreErrorColumn(0);
      setCoreErrorPosition(-1);
      setCoreParseMode(result.mode);
    } catch (err) {
      applyCoreSourceFailure(text, err, focusOnError);
    }
  };

  const applyCoreAndFormat = ({ focusOnError = true } = {}) => {
    applyCoreSourceText(coreInputText, { formatOnSuccess: true, focusOnError });
  };

  const onCoreEditorLiveSync = (e) => {
    applyCoreSourceText(e.target.value, { formatOnSuccess: false, focusOnError: false });
  };

  const onCoreEditorPaste = () => {
    requestAnimationFrame(() => {
      const el = coreInputRef.current;
      if (!el) return;
      applyCoreSourceText(el.value, { formatOnSuccess: false, focusOnError: false });
    });
  };

  const getDraftSettingsForSubmit = () => {
    try {
      const result = parseCoreInput(coreInputText);
      setCoreParseError('');
      setCoreLineHint('');
      setCoreErrorLine(0);
      setCoreErrorColumn(0);
      setCoreErrorPosition(-1);
      setCoreParseMode(result.mode);
      return {
        ...draftSettings,
        core: result.parsed,
      };
    } catch (err) {
      const msg = err?.message || '解析失败';
      let pos = extractErrorPosition(msg);
      let loc = getLineColumnByPosition(coreInputText, pos);
      if (loc.line <= 0 || loc.column <= 0) {
        const lc = extractErrorLineColumn(msg);
        if (lc.line > 0 && lc.column > 0) {
          loc = lc;
          pos = getPositionByLineColumn(coreInputText, lc.line, lc.column);
        }
      }
      setCoreParseError(msg);
      setCoreLineHint(pos >= 0 ? `错误大致在第 ${pos} 个字符附近。` : '');
      setCoreErrorLine(loc.line);
      setCoreErrorColumn(loc.column);
      setCoreErrorPosition(pos);
      setCoreParseMode('');
      throw new Error(`core 参数格式不合法：${msg}`);
    }
  };

  const coreErrorContext = useMemo(
    () => getErrorContextLines(coreInputText, coreErrorLine, 2),
    [coreInputText, coreErrorLine],
  );

  useEffect(() => {
    if (coreErrorPosition < 0 || !coreInputRef.current) return;
    const textarea = coreInputRef.current;
    const pos = Math.max(0, Math.min(coreErrorPosition, coreInputText.length));
    textarea.focus();
    textarea.setSelectionRange(pos, Math.min(pos + 1, coreInputText.length));
    const lineNo = coreInputText.slice(0, pos).split('\n').length;
    const lineHeight = 22;
    textarea.scrollTop = Math.max(0, (lineNo - 2) * lineHeight);
  }, [coreErrorPosition, coreInputText]);

  return children({
    draftSettings,
    updateSection,
    setDraftSettings,
    coreEditor: {
      value: coreInputText,
      onChange: (nextText) => {
        setCoreInputText(nextText);
      },
      onKeyUp: onCoreEditorLiveSync,
      onPaste: onCoreEditorPaste,
      onBlur: () => applyCoreSourceText(coreInputText, { formatOnSuccess: true, focusOnError: false }),
      onApply: applyCoreAndFormat,
      inputRef: coreInputRef,
      parseError: coreParseError,
      lineHint: coreLineHint,
      errorLine: coreErrorLine,
      errorColumn: coreErrorColumn,
      errorContext: coreErrorContext,
      parseMode: coreParseMode,
      getDraftSettingsForSubmit,
    },
  });
}

export default StrategySettingsContainer;
