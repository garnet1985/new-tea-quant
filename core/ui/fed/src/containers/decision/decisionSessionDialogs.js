import React, { useMemo } from 'react';
import { Button, DataGrid, Dialog, Tag } from 'ui';
import { formatDateTime } from '../../service/format/formatDateTime';
import { unfinishedSessions } from './decisionSessionPick';
import './decisionSessionDialogs.scss';

function statusChip(status) {
  const completed = status === 'completed';
  return (
    <Tag
      size="sm"
      status={completed ? 'success' : 'warning'}
      variant="outline"
    >
      {completed ? '已完成' : '进行中'}
    </Tag>
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
      { field: 'dmId', headerName: '#', width: 72 },
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
              variant="primary"
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
            <div className="ntq-decision-session-actions">
              <Button
                variant="glass"
                disabled={busy || isCurrent}
                onClick={() => onSelect(params.row.dmId)}
              >
                {isCurrent ? '当前' : (completed ? '回看' : '进入')}
              </Button>
              <Button
                variant="danger"
                disabled={busy}
                onClick={() => onDelete(params.row)}
              >
                删除
              </Button>
            </div>
          );
        },
      },
    ];
  }, [busy, current, onDelete, onSelect, panel]);

  return (
    <Dialog
      open={Boolean(panel)}
      onClose={onClose}
      title={(
        <span className="ntq-decision-session-dialog__title">
          <span>
            {panel === 'continue' ? '选择要继续的模拟回测' : '管理模拟回测'}
          </span>
          <Button variant="ghost" onClick={onClose}>关闭</Button>
        </span>
      )}
      size="lg"
    >
      <p className="ntq-muted">
        {panel === 'continue'
          ? '只能选择进行中的模拟回测继续。时钟停在该次回测上次停留的交易日。'
          : '进入或回看会打开该次回测当时的时钟；删除不可恢复。'}
      </p>
      <DataGrid
        autoHeight
        bordered={false}
        rows={rows}
        columns={columns}
        getRowId={(row) => row.id || row.dmId}
        hideFooter
      />
    </Dialog>
  );
}
