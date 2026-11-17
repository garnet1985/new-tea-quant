import React from 'react';
import Message from 'ui/message/message';
import { Button, TextArea } from 'ui';
import './style.scss';

function PythonDictInputPanel({
  value,
  onChange,
  onApply,
  onLoadDefault,
  onLoadLarge,
  onConvertPythonLiteral,
  parseError,
  lineHint,
  errorLine,
  errorColumn,
  errorContext = [],
  inputRef,
  title = '左栏：Raw JSON 输入',
}) {
  return (
    <div className="ntq-python-dict-input-panel">
      <h3 className="ntq-python-dict-input-panel__title">{title}</h3>

      <div className="ntq-python-dict-input-panel__actions">
        <Button variant="primary" onClick={onApply}>
          验证 JSON
        </Button>
        <Button variant="glass" onClick={onLoadDefault}>
          加载默认样例
        </Button>
        <Button variant="glass" onClick={onLoadLarge}>
          加载大样例（性能）
        </Button>
        <Button variant="glass" onClick={onConvertPythonLiteral}>
          尝试转换 Python 字面量
        </Button>
      </div>

      {parseError ? (
        <Message status="error">
          <p className="ntq-python-dict-input-panel__error-main">{parseError}</p>
          {lineHint ? (
            <p className="ntq-python-dict-input-panel__error-hint">{lineHint}</p>
          ) : null}
          {errorLine > 0 ? (
            <p className="ntq-python-dict-input-panel__error-hint">
              定位到第 {errorLine} 行，第 {errorColumn} 列。
            </p>
          ) : null}
        </Message>
      ) : null}

      <TextArea
        labelPlacement="none"
        maxWidth={false}
        rows={26}
        inputRef={inputRef}
        error={parseError && errorLine > 0
          ? `错误定位：第 ${errorLine} 行，第 ${errorColumn} 列（已跳转）`
          : (parseError || '')}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入 JSON（例如 settings.core）"
      />

      <Message status="info">
        支持两种输入：1) 标准 JSON；2) Python dict 风格（支持单引号、True/False/None、# 注释）。
      </Message>

      {parseError && errorContext.length > 0 ? (
        <div className="ntq-python-dict-input-panel__context">
          <p className="ntq-python-dict-input-panel__context-label">错误上下文（已高亮）</p>
          <pre className="ntq-python-dict-input-panel__context-pre">
            {errorContext.map((row) => (
              <div
                key={row.lineNo}
                className={[
                  'ntq-python-dict-input-panel__context-line',
                  row.isError ? 'is-error' : '',
                ].filter(Boolean).join(' ')}
              >
                {String(row.lineNo).padStart(4, ' ')} | {row.text}
              </div>
            ))}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

export default PythonDictInputPanel;
