import React from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Stack,
  Typography,
} from '@mui/material';
import NtqIcon from '../../components/ntqIcon/ntqIcon';

function stateIcon(row, runningStep) {
  if (runningStep && row.id === runningStep) {
    return (
      <Stack direction="row" spacing={1} alignItems="center" className="setup-step-state">
        <NtqIcon name="refresh" size={20} spin />
        <Typography variant="body2">执行中...</Typography>
      </Stack>
    );
  }
  if (row.state === '已完成') {
    return (
      <Stack direction="row" spacing={1} alignItems="center">
        <NtqIcon name="success" size={20} tone="success" />
        <Typography variant="body2">已完成</Typography>
      </Stack>
    );
  }
  if (row.state === '失败') {
    return (
      <Stack direction="row" spacing={1} alignItems="center">
        <NtqIcon name="cancel" size={20} tone="error" />
        <Typography variant="body2">失败</Typography>
      </Stack>
    );
  }
  if (row.state === '待输入') {
    return (
      <Stack direction="row" spacing={1} alignItems="center">
        <NtqIcon name="radioUnchecked" size={20} tone="warning" />
        <Typography variant="body2">待输入</Typography>
      </Stack>
    );
  }
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <NtqIcon name="radioUnchecked" size={20} tone="disabled" />
      <Typography variant="body2">{row.state}</Typography>
    </Stack>
  );
}

function SetupExecutionPanel({
  flowStage,
  progressText,
  runningStep,
  importProgress,
  pollWarning,
  rows,
}) {
  if (flowStage !== 'executing') return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>
          自动执行步骤
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          {progressText}
        </Typography>
        {pollWarning ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {pollWarning}
          </Alert>
        ) : null}
        {runningStep === 'import_data' && importProgress.totalTables > 0 ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            导入进度：{importProgress.completedCount}/{importProgress.totalTables}
            （{importProgress.percent}%）
            {importProgress.currentTable ? `，当前表：${importProgress.currentTable}` : ''}
          </Alert>
        ) : null}
        <Stack spacing={1} className="setup-page__step-list">
          {rows.map((row) => (
            <Box key={row.id} className="setup-page__step-row">
              <Typography variant="body2" className="setup-page__step-row-index">
                {row.order}
              </Typography>
              <Box className="setup-page__step-row-main">
                <Typography variant="body2">{row.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {row.detail}
                </Typography>
              </Box>
              {stateIcon(row, runningStep)}
            </Box>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}

export default SetupExecutionPanel;
