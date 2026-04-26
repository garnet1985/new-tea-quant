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

function DictParserField({ field, context = {} }) {
  const sourceKey = field.sourceKey || field.name;
  const parser = context?.[sourceKey];

  if (!parser) {
    return (
      <Alert severity="warning">
        Dict parser source not found: <strong>{sourceKey}</strong>
      </Alert>
    );
  }

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
        <Button variant="contained" size="small" onClick={parser.onApply}>
          应用并格式化
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
          支持 JSON / Python dict 风格输入
        </Typography>
      </Stack>

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
      ) : null}

      {!parser.parseError && parser.parseMode ? (
        <Alert severity="success" sx={{ mb: 1 }}>
          已应用，当前解析模式：{parser.parseMode}
        </Alert>
      ) : null}

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

      <TextField
        multiline
        fullWidth
        inputRef={parser.inputRef}
        error={Boolean(parser.parseError)}
        value={parser.value}
        onChange={(e) => parser.onChange(e.target.value)}
        placeholder={field.placeholder || '输入 settings.core（dict）'}
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

export default DictParserField;
