import React from 'react';
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

function CoreDictEditorView({
  value,
  onChange,
  onApply,
  inputRef,
  parseError,
  lineHint,
  errorLine,
  errorColumn,
  errorContext = [],
  parseMode,
}) {
  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
        <Button variant="contained" size="small" onClick={onApply}>
          应用并格式化
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
          支持 JSON / Python dict 风格输入
        </Typography>
      </Stack>

      {parseError ? (
        <Alert severity="error" sx={{ mb: 1 }}>
          <Typography variant="body2">{parseError}</Typography>
          {lineHint ? (
            <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
              {lineHint}
            </Typography>
          ) : null}
          {errorLine > 0 ? (
            <Typography variant="caption" component="div" sx={{ mt: 0.5 }}>
              定位到第 {errorLine} 行，第 {errorColumn} 列。
            </Typography>
          ) : null}
        </Alert>
      ) : null}

      {!parseError && parseMode ? (
        <Alert severity="success" sx={{ mb: 1 }}>
          已应用，当前解析模式：{parseMode}
        </Alert>
      ) : null}

      {parseError && errorContext.length > 0 ? (
        <Paper variant="outlined" sx={{ mb: 1, p: 1, backgroundColor: 'grey.50' }}>
          <Typography variant="caption" color="text.secondary">
            错误上下文（已高亮）
          </Typography>
          <Box component="pre" sx={{ m: 0, mt: 0.5, fontSize: 12, overflowX: 'auto' }}>
            {errorContext.map((row) => (
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

      <TextField
        multiline
        fullWidth
        inputRef={inputRef}
        error={Boolean(parseError)}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入 settings.core（dict）"
        sx={{
          '& .MuiInputBase-root': {
            alignItems: 'flex-start',
          },
          '& .MuiInputBase-inputMultiline': {
            height: '300px !important',
            overflow: 'auto !important',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: 13,
            lineHeight: 1.5,
          },
        }}
      />
    </Box>
  );
}

export default CoreDictEditorView;
