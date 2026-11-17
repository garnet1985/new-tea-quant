import React from 'react';
import Button from 'ui/button/button';
import Block from 'ui/layout/block';
import Message from 'ui/message/message';
import TextArea from 'ui/input/textArea';
import Heading from 'ui/text/heading';
import './style.scss';

/**
 * JSON / Python dict 编辑面板（验证、样例、错误定位）。
 * 属 NTQ 特有复合组件，不放在通用 input 下。
 * onChange 接收字符串（非事件），与旧 views/pythonDictInputPanel 对齐。
 *
 * @example
 * <PythonDictEditor value={text} onChange={setText} onApply={validate} parseError={err} />
 */
function PythonDictEditor({
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
  className = '',
}) {
  const context = Array.isArray(errorContext) ? errorContext : [];
  const locateHint = parseError && errorLine > 0
    ? `错误定位：第 ${errorLine} 行，第 ${errorColumn} 列（已跳转）`
    : '';

  return (
    <Block
      surface="soft"
      bordered
      radius="md"
      padding="md"
      gap="md"
      className={['ntq-python-dict-panel', className].filter(Boolean).join(' ')}
    >
      <Heading level="h4" gap="none">{title}</Heading>

      <div className="ntq-python-dict-panel__actions">
        {typeof onApply === 'function' ? (
          <Button variant="primary" onClick={onApply}>验证 JSON</Button>
        ) : null}
        {typeof onLoadDefault === 'function' ? (
          <Button variant="ghost" onClick={onLoadDefault}>加载默认样例</Button>
        ) : null}
        {typeof onLoadLarge === 'function' ? (
          <Button variant="ghost" onClick={onLoadLarge}>加载大样例（性能）</Button>
        ) : null}
        {typeof onConvertPythonLiteral === 'function' ? (
          <Button variant="ghost" onClick={onConvertPythonLiteral}>
            尝试转换 Python 字面量
          </Button>
        ) : null}
      </div>

      {parseError ? (
        <Message status="error">
          <div className="ntq-python-dict-panel__error">
            <p className="ntq-python-dict-panel__error-main">{parseError}</p>
            {lineHint ? (
              <p className="ntq-python-dict-panel__error-meta ntq-muted">{lineHint}</p>
            ) : null}
            {errorLine > 0 ? (
              <p className="ntq-python-dict-panel__error-meta ntq-muted">
                {`定位到第 ${errorLine} 行，第 ${errorColumn} 列。`}
              </p>
            ) : null}
          </div>
        </Message>
      ) : null}

      <TextArea
        labelPlacement="none"
        maxWidth={false}
        rows={18}
        value={value ?? ''}
        onChange={(e) => {
          if (typeof onChange === 'function') onChange(e.target.value);
        }}
        error={locateHint}
        placeholder="输入 JSON（例如 settings.core）"
        inputRef={inputRef}
        aria-label={title || 'JSON 输入'}
      />

      <Message status="info">
        支持两种输入：1) 标准 JSON；2) Python dict 风格（单引号、True/False/None、# 注释）。
      </Message>

      {parseError && context.length > 0 ? (
        <Block
          surface="panel"
          bordered
          radius="sm"
          padding="sm"
          gap="xs"
          className="ntq-python-dict-panel__context"
        >
          <p className="ntq-muted ntq-python-dict-panel__context-title">错误上下文（已高亮）</p>
          <pre className="ntq-python-dict-panel__context-pre">
            {context.map((row) => (
              <div
                key={row.lineNo}
                className={[
                  'ntq-python-dict-panel__context-line',
                  row.isError ? 'is-error' : '',
                ].filter(Boolean).join(' ')}
              >
                {`${String(row.lineNo).padStart(4, ' ')} | ${row.text}`}
              </div>
            ))}
          </pre>
        </Block>
      ) : null}
    </Block>
  );
}

export default PythonDictEditor;
