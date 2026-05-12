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
    <Paper variant="outlined" sx={{ p: 2, flex: 1, minWidth: 0 }}>
      <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
        {title}
      </Typography>

      <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} flexWrap="wrap">
        <Button variant="contained" onClick={onApply}>
          验证 JSON
        </Button>
        <Button variant="outlined" onClick={onLoadDefault}>
          加载默认样例
        </Button>
        <Button variant="outlined" onClick={onLoadLarge}>
          加载大样例（性能）
        </Button>
        <Button variant="outlined" onClick={onConvertPythonLiteral}>
          尝试转换 Python 字面量
        </Button>
      </Stack>

      {parseError ? (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ mb: lineHint ? 0.5 : 0 }}>
            {parseError}
          </Typography>
          {lineHint ? (
            <Typography variant="caption" component="div">
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

      <TextField
        multiline
        minRows={26}
        maxRows={32}
        fullWidth
        inputRef={inputRef}
        error={Boolean(parseError)}
        helperText={
          parseError && errorLine > 0
            ? `错误定位：第 ${errorLine} 行，第 ${errorColumn} 列（已跳转）`
            : ''
        }
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入 JSON（例如 settings.core）"
      />

      <Alert severity="info" sx={{ mt: 1.5 }}>
        支持两种输入：1) 标准 JSON；2) Python dict 风格（支持单引号、True/False/None、# 注释）。
      </Alert>

      {parseError && errorContext.length > 0 ? (
        <Paper variant="outlined" sx={{ mt: 1.5, p: 1, backgroundColor: 'grey.50' }}>
          <Typography variant="caption" color="text.secondary">
            错误上下文（已高亮）
          </Typography>
          <Box component="pre" sx={{ m: 0, mt: 0.75, fontSize: 12, overflowX: 'auto' }}>
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
    </Paper>
  );
}

export default PythonDictInputPanel;
