import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Pagination,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import VersionPickLabel from './versionPickLabel';
import { versionPickSearchText } from './versionPickMarks';
import { formatVersionPickTime } from '../../utils/formatDateTime';
import './versionPickerDialog.scss';

export const VERSION_PICKER_PAGE_SIZE = 8;

function VersionPickerDialog({
  open,
  onClose,
  versions = [],
  selectedId = '',
  excludeIds = [],
  onSelect,
  title,
  titleExtra,
  emptyHint = '暂无可选版本。',
  noMatchHint = '没有匹配的版本。',
  allowClear = false,
  clearLabel = '不对比',
  renderSecondaryAction,
  closeOnSelect = true,
  dialogSx,
}) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!open) return undefined;
    setSearch('');
    setPage(1);
    return undefined;
  }, [open]);

  const exclude = useMemo(
    () => new Set((Array.isArray(excludeIds) ? excludeIds : []).map((id) => String(id || '').trim()).filter(Boolean)),
    [excludeIds],
  );

  const pool = useMemo(() => {
    const rows = Array.isArray(versions) ? versions : [];
    if (exclude.size === 0) return rows;
    return rows.filter((version) => !exclude.has(String(version?.id || '').trim()));
  }, [versions, exclude]);

  const filtered = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    if (!keyword) return pool;
    return pool.filter((version) => versionPickSearchText(version).toLowerCase().includes(keyword));
  }, [pool, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / VERSION_PICKER_PAGE_SIZE) || 1);
  const currentPage = Math.min(page, totalPages);
  const slice = useMemo(() => {
    const start = (currentPage - 1) * VERSION_PICKER_PAGE_SIZE;
    return filtered.slice(start, start + VERSION_PICKER_PAGE_SIZE);
  }, [filtered, currentPage]);

  const selected = String(selectedId || '').trim();
  const hasActions = typeof renderSecondaryAction === 'function';

  const pick = (versionId) => {
    onSelect?.(versionId);
    if (closeOnSelect) onClose?.();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth sx={dialogSx}>
      <DialogTitle sx={{ pr: 3 }}>
        <Stack direction="row" alignItems="baseline" justifyContent="space-between" spacing={2}>
          <Box component="span" sx={{ flexShrink: 0 }}>{title}</Box>
          {titleExtra || null}
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={1}>
          <TextField
            size="small"
            fullWidth
            placeholder="搜索版本 ID、时间或标记"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
          <Typography variant="caption" color="text.secondary">
            {pool.length > 0
              ? `共 ${filtered.length} 条${filtered.length !== pool.length ? `（已筛选，全部 ${pool.length} 条）` : ''}`
              : emptyHint}
          </Typography>
          <List className="ntq-version-picker-dialog__list">
            {allowClear ? (
              <ListItem disablePadding>
                <ListItemButton selected={!selected} onClick={() => pick('')}>
                  <ListItemText primary={clearLabel} />
                </ListItemButton>
              </ListItem>
            ) : null}
            {slice.length > 0 ? slice.map((version) => (
              <ListItem
                key={version.id}
                disablePadding
                secondaryAction={hasActions ? renderSecondaryAction(version) : null}
              >
                <ListItemButton
                  selected={version.id === selected}
                  sx={hasActions ? { pr: 14 } : undefined}
                  onClick={() => pick(version.id)}
                >
                  <ListItemText
                    primary={<VersionPickLabel version={version} />}
                    secondary={formatVersionPickTime(version)}
                  />
                </ListItemButton>
              </ListItem>
            )) : null}
            {slice.length === 0 && !(allowClear && pool.length === 0) ? (
              <Box className="ntq-version-picker-dialog__empty">
                <Typography variant="body2" color="text.secondary">
                  {pool.length > 0 ? noMatchHint : emptyHint}
                </Typography>
              </Box>
            ) : null}
          </List>
          {filtered.length > VERSION_PICKER_PAGE_SIZE ? (
            <Box className="ntq-version-picker-dialog__pages">
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={(_event, nextPage) => setPage(nextPage)}
                size="small"
                color="primary"
              />
            </Box>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>关闭</Button>
      </DialogActions>
    </Dialog>
  );
}

export default VersionPickerDialog;
