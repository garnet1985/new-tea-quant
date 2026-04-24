import React from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';

function SetupExecutionPanel({
  flowStage,
  progressText,
  runningStep,
  importProgress,
  rows,
  executingColumns,
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
        {runningStep === 'import_data' && importProgress.totalTables > 0 ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            导入进度：{importProgress.completedCount}/{importProgress.totalTables}
            （{importProgress.percent}%）
            {importProgress.currentTable ? `，当前表：${importProgress.currentTable}` : ''}
          </Alert>
        ) : null}
        <Box sx={{ height: 320 }}>
          <DataGrid
            rows={rows}
            columns={executingColumns}
            disableRowSelectionOnClick
            hideFooter
          />
        </Box>
      </CardContent>
    </Card>
  );
}

export default SetupExecutionPanel;
