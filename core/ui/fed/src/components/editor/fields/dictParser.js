import React, { useEffect, useState } from 'react';
import NtqIcon from '../../ntqIcon/ntqIcon';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import EditorFieldLabel from './editorFieldLabel';

/** 与 ``TextField`` multiline 输入一致，供只读 JSON / diff 视图复用核心设置编辑区观感 */
export const DICT_PARSER_TEXT_FONT = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  fontSize: 'var(--ntq-form-control-font-size, 14px)',
  lineHeight: 'var(--ntq-form-control-line-height, 1.5)',
};

const COMPACT_EDITOR_HEIGHT = 300;

function getTextFieldSx({ fullscreen = false } = {}) {
  return {
    ...(fullscreen ? { height: '100%', display: 'flex', flexDirection: 'column' } : {}),
    '& .MuiOutlinedInput-root': {
      padding: '8px 12px',
      alignItems: 'flex-start',
      ...(fullscreen ? { flex: 1, height: '100%' } : {}),
    },
    '& .MuiInputBase-inputMultiline': {
      height: fullscreen ? '100% !important' : `${COMPACT_EDITOR_HEIGHT}px !important`,
      minHeight: fullscreen ? 'min(72vh, 720px) !important' : undefined,
      overflow: 'auto !important',
      padding: '0 !important',
      boxSizing: 'border-box',
      whiteSpace: 'pre',
      tabSize: 2,
      ...DICT_PARSER_TEXT_FONT,
    },
  };
}

function DictParserStatusAlerts({ parser }) {
  return (
    <>
      {parser.parseError ? (
        <Alert severity="error" sx={{ mb: 1 }}>
          <Typography variant="body2">{parser.parseError}</Typography>
          {parser.lineHint ? (
            <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
              {parser.lineHint}
            </Typography>
          ) : null}
          {parser.errorLine > 0 ? (
            <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
              定位到第 {parser.errorLine} 行，第 {parser.errorColumn} 列。
            </Typography>
          ) : null}
        </Alert>
      ) : (
        <Alert severity="success" sx={{ mb: 1 }}>
          格式正确
        </Alert>
      )}

      {parser.parseError && Array.isArray(parser.errorContext) && parser.errorContext.length > 0 ? (
        <Paper variant="outlined" sx={{ mb: 1, p: 1, backgroundColor: 'grey.50' }}>
          <Typography variant="caption" color="text.secondary">
            错误上下文（已高亮）
          </Typography>
          <Box component="pre" sx={{ m: 0, mt: 0.5, fontSize: 12, overflowX: 'auto' }}>
            {parser.errorContext.map((row) => (
              <Box
                key={row.lineNo}
                component="div"
                sx={{
                  px: 0.5,
                  borderRadius: 0.5,
                  backgroundColor: row.isError ? 'error.light' : 'transparent',
                  color: row.isError ? 'error.contrastText' : 'text.primary',
                }}
              >
                {String(row.lineNo).padStart(4, ' ')} | {row.text}
              </Box>
            ))}
          </Box>
        </Paper>
      ) : null}
    </>
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
    <TextField
      multiline
      fullWidth
      autoFocus={autoFocus}
      inputRef={inputRef}
      error={Boolean(parser.parseError)}
      value={parser.value}
      onChange={(e) => parser.onChange(e.target.value)}
      onBlur={parser.onBlur}
      onKeyUp={parser.onKeyUp}
      onPaste={parser.onPaste}
      placeholder={field.placeholder || '输入 settings.core（dict）'}
      sx={getTextFieldSx({ fullscreen })}
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
      size="small"
      variant="outlined"
      onClick={parser.onResetToDefault}
      disabled={isAtDefault}
    >
      恢复默认
    </Button>
  ) : null;

  const windowBtn = variant === 'fullscreen' ? (
    <Button
      size="small"
      variant="outlined"
      startIcon={<NtqIcon name="remove" size={18} />}
      onClick={onCollapse}
    >
      回到侧边栏
    </Button>
  ) : (
    <Button
      size="small"
      variant="outlined"
      startIcon={<NtqIcon name="add" size={18} />}
      onClick={onExpand}
    >
      在大窗口编辑
    </Button>
  );

  return (
    <Stack spacing={1} sx={{ mb: 1 }}>
      <EditorFieldLabel field={field} context={context} sx={{ mb: 0 }} />
      <Stack
        direction="row"
        spacing={0.75}
        alignItems="center"
        useFlexGap
        flexWrap="wrap"
      >
        {windowBtn}
        {resetBtn}
      </Stack>
    </Stack>
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
      <Alert severity="warning">
        Dict parser source not found: <strong>{sourceKey}</strong>
      </Alert>
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
    <Box className="ntq-dict-parser-field">
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
      >
        <DialogTitle sx={{ py: 1.25 }}>
          <DictParserToolbar
            field={field}
            context={context}
            parser={parser}
            canReset={canReset}
            isAtDefault={isAtDefault}
            variant="fullscreen"
            onCollapse={() => setFullscreenOpen(false)}
          />
        </DialogTitle>
        <DialogContent
          dividers
          sx={{
            display: 'flex',
            flexDirection: 'column',
            pt: 1.5,
            pb: 2,
          }}
        >
          <DictParserStatusAlerts parser={parser} />
          <Box sx={{ flex: 1, minHeight: 'min(72vh, 720px)', display: 'flex' }}>
            <DictParserTextarea
              parser={parser}
              field={field}
              inputRef={parser.fullscreenInputRef}
              fullscreen
              autoFocus
            />
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
}

export default DictParserField;
