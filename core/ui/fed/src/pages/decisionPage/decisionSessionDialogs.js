import React, { useMemo } from 'react';
import {
  Button,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import { zhCN } from '@mui/x-data-grid/locales';
import { NTQ_DATA_GRID_LOADING_SLOTS } from '../../components/dataGridLoadingOverlay/dataGridLoadingOverlay';
import { formatDateTime } from '../../utils/formatDateTime';
import { unfinishedSessions } from './decisionSessionPick';

function statusChip(status) {
  const completed = status === 'completed';
  return (
    <Chip
      size="small"
      label={completed ? '已完成' : '进行中'}
      color={completed ? 'success' : 'warning'}
      variant="outlined"
    />
  );
}

export default function DecisionSessionDialogs({
  panel,
  onClose,
  sessions,
  currentSessionId,
  onSelect,
  onDelete,
  busy,
}) {
  const unfinished = useMemo(() => unfinishedSessions(sessions), [sessions]);
  const rows = panel === 'continue' ? unfinished : sessions;
  const current = String(currentSessionId || '').trim();

  const columns = useMemo(() => {
    const base = [
      { field: 'dmId', headerName: '局', width: 72 },
      {
        field: 'status',
        headerName: '状态',
        width: 120,
        renderCell: (params) => statusChip(params.value),
      },
      { field: 'date', headerName: '停在', minWidth: 128, flex: 0.6 },
      {
        field: 'updatedAt',
        headerName: '更新',
        minWidth: 140,
        flex: 0.8,
        valueFormatter: (params) => formatDateTime(params.value),
      },
    ];
    if (panel === 'continue') {
      return [
        ...base,
        {
          field: 'actions',
          headerName: '操作',
          sortable: false,
          minWidth: 120,
          flex: 0.5,
          renderCell: (params) => (
            <Button
              size="small"
              variant="contained"
              disabled={busy || params.row.dmId === current}
              onClick={() => onSelect(params.row.dmId)}
            >
              {params.row.dmId === current ? '当前' : '继续'}
            </Button>
          ),
        },
      ];
    }
    return [
      ...base,
      {
        field: 'actions',
        headerName: '操作',
        sortable: false,
        minWidth: 220,
        flex: 1,
        renderCell: (params) => {
          const isCurrent = params.row.dmId === current;
          const completed = params.row.status === 'completed';
          return (
            <Stack direction="row" spacing={1}>
              <Button
                size="small"
                variant="outlined"
                disabled={busy || isCurrent}
                onClick={() => onSelect(params.row.dmId)}
              >
                {isCurrent ? '当前' : (completed ? '回看' : '进入')}
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="error"
                disabled={busy}
                onClick={() => onDelete(params.row)}
              >
                删除
              </Button>
            </Stack>
          );
        },
      },
    ];
  }, [busy, current, onDelete, onSelect, panel]);

  return (
    <Dialog open={Boolean(panel)} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="baseline" justifyContent="space-between" spacing={2}>
          <Typography variant="h6" component="span">
            {panel === 'continue' ? '选择要继续的一局' : '管理对局'}
          </Typography>
          <Button size="small" onClick={onClose}>关闭</Button>
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          {panel === 'continue'
            ? '只能选进行中的局接着下。时钟停在该局上次停留的交易日。'
            : '进入或回看会打开该局当时的时钟；删除不可恢复。'}
        </Typography>
        <DataGrid
          autoHeight
          rows={rows}
          columns={columns}
          getRowId={(row) => row.id || row.dmId}
          localeText={zhCN.components.MuiDataGrid.defaultProps.localeText}
          hideFooter
          disableRowSelectionOnClick
          slots={NTQ_DATA_GRID_LOADING_SLOTS}
          sx={{ border: 0, '& .MuiDataGrid-cell': { py: 1 } }}
        />
      </DialogContent>
    </Dialog>
  );
}
