import React, { useEffect, useState } from 'react';
import { Button, Dialog, Message, TextArea } from 'ui';
import EditorFieldLabel from './editorFieldLabel';
import './style.scss';

/** 与 dict 编辑区一致，供 JSON / diff 视图复用 */
export const DICT_PARSER_TEXT_FONT = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  fontSize: 'var(--ntq-form-control-font-size, 14px)',
  lineHeight: 'var(--ntq-form-control-line-height, 1.5)',
};

const COMPACT_EDITOR_HEIGHT = 300;

function DictParserStatusAlerts({ parser }) {
  return (
    <div className="ntq-dict-parser-field__status">
      {parser.parseError ? (
        <Message status="error">
          <div className="ntq-dict-parser-field__alert-body">
            <p className="ntq-dict-parser-field__alert-text">{parser.parseError}</p>
            {parser.lineHint ? (
              <p className="ntq-dict-parser-field__alert-meta">{parser.lineHint}</p>
            ) : null}
            {parser.errorLine > 0 ? (
              <p className="ntq-dict-parser-field__alert-meta">
                定位到第 {parser.errorLine} 行，第 {parser.errorColumn} 列。
              </p>
            ) : null}
          </div>
        </Message>
      ) : (
        <Message status="success">
          格式正确
        </Message>
      )}

      {parser.parseError && Array.isArray(parser.errorContext) && parser.errorContext.length > 0 ? (
        <div className="ntq-dict-parser-field__context">
          <p className="ntq-dict-parser-field__context-label ntq-muted">
            错误上下文（已高亮）
          </p>
          <pre className="ntq-dict-parser-field__context-pre">
            {parser.errorContext.map((row) => (
              <div
                key={row.lineNo}
                className={[
                  'ntq-dict-parser-field__context-line',
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

function DictParserTextarea({
  parser,
  field,
  inputRef,
  fullscreen = false,
  autoFocus = false,
}) {
  return (
    <TextArea
      labelPlacement="none"
      maxWidth={false}
      autoFocus={autoFocus}
      inputRef={inputRef}
      value={parser.value}
      onChange={(e) => parser.onChange(e.target.value)}
      onBlur={parser.onBlur}
      onKeyUp={parser.onKeyUp}
      onPaste={parser.onPaste}
      placeholder={field.placeholder || '输入 settings.core（dict）'}
      className={[
        'ntq-dict-parser-field__textarea',
        fullscreen ? 'ntq-dict-parser-field__textarea--fullscreen' : 'ntq-dict-parser-field__textarea--compact',
        parser.parseError ? 'is-error' : '',
      ].filter(Boolean).join(' ')}
      // 紧凑模式勿用大 minRows：MUI 按行高测算时会吃到固定 height，叠出上千 px
      rows={fullscreen ? 24 : 4}
      InputProps={{
        sx: fullscreen
          ? { flex: 1, height: '100%', alignItems: 'flex-start' }
          : {
            alignItems: 'flex-start',
            height: COMPACT_EDITOR_HEIGHT,
            maxHeight: COMPACT_EDITOR_HEIGHT,
            overflow: 'hidden',
          },
      }}
      inputProps={{
        style: {
          ...DICT_PARSER_TEXT_FONT,
          whiteSpace: 'pre',
          tabSize: 2,
          height: '100%',
          maxHeight: fullscreen ? undefined : '100%',
          minHeight: fullscreen ? 'min(72vh, 720px)' : 0,
          overflow: 'auto',
          boxSizing: 'border-box',
          resize: fullscreen ? undefined : 'none',
        },
      }}
    />
  );
}

function DictParserToolbar({
  field,
  context,
  parser,
  canReset,
  isAtDefault,
  variant = 'compact',
  onExpand,
  onCollapse,
}) {
  const resetBtn = canReset ? (
    <Button
      variant="glass"
      onClick={parser.onResetToDefault}
      disabled={isAtDefault}
    >
      恢复默认
    </Button>
  ) : null;

  const windowBtn = variant === 'fullscreen' ? (
    <Button
      variant="glass"
      icon="delete"
      onClick={onCollapse}
    >
      回到侧边栏
    </Button>
  ) : (
    <Button
      variant="glass"
      icon="add"
      onClick={onExpand}
    >
      在大窗口编辑
    </Button>
  );

  return (
    <div className="ntq-dict-parser-field__toolbar">
      <EditorFieldLabel field={field} context={context} noMargin />
      <div className="ntq-dict-parser-field__actions">
        {windowBtn}
        {resetBtn}
      </div>
    </div>
  );
}

function DictParserField({ field, context = {} }) {
  const sourceKey = field.sourceKey || field.name;
  const parser = context?.[sourceKey];
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

  useEffect(() => {
    if (!fullscreenOpen) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setFullscreenOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [fullscreenOpen]);

  if (!parser) {
    return (
      <Message status="warning">
        Dict parser source not found: <strong>{sourceKey}</strong>
      </Message>
    );
  }

  const canReset = typeof parser.onResetToDefault === 'function';
  const isAtDefault = canReset
    && String(parser.value ?? '').trim() === String(parser.defaultCoreText ?? '').trim();

  const toolbarProps = {
    field,
    context,
    parser,
    canReset,
    isAtDefault,
    onExpand: () => setFullscreenOpen(true),
  };

  return (
    <div className="ntq-dict-parser-field">
      <DictParserToolbar {...toolbarProps} />
      <DictParserStatusAlerts parser={parser} />
      <DictParserTextarea
        parser={parser}
        field={field}
        inputRef={parser.inputRef}
      />

      <Dialog
        fullScreen
        open={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        title={(
          <DictParserToolbar
            field={field}
            context={context}
            parser={parser}
            canReset={canReset}
            isAtDefault={isAtDefault}
            variant="fullscreen"
            onCollapse={() => setFullscreenOpen(false)}
          />
        )}
      >
        <DictParserStatusAlerts parser={parser} />
        <div className="ntq-dict-parser-field__fullscreen-body">
          <DictParserTextarea
            parser={parser}
            field={field}
            inputRef={parser.fullscreenInputRef}
            fullscreen
            autoFocus
          />
        </div>
      </Dialog>
    </div>
  );
}

export default DictParserField;
