import React from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  ListItemText,
  Pagination,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

function StrategyDesignMetaDialogs() {
  const wb = useStrategyDesignWorkbenchContext();

  return (
    <>
      <Dialog open={wb.confirmOpen} onClose={() => wb.setConfirmOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>恢复历史版本配置</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2">
            将把版本
            {' '}
            <strong>{wb.pendingVersionId}</strong>
            {' '}
            当时冻结的配置写回 settings.py，并刷新当前编辑器。未保存的草稿将被覆盖。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => wb.setConfirmOpen(false)}>取消</Button>
          <Button
            variant="contained"
            disabled={wb.isSavingSettings}
            onClick={wb.confirmRestoreVersion}
          >
            {wb.isSavingSettings ? '处理中...' : '确认恢复'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={wb.moreVersionsOpen} onClose={wb.closeVersionsDialog} maxWidth="sm" fullWidth>
        <DialogTitle>选择工作台版本</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1}>
            <TextField
              size="small"
              fullWidth
              placeholder="搜索版本 ID、创建或更新时间"
              value={wb.versionSearch}
              onChange={(event) => wb.setVersionSearch(event.target.value)}
            />
            <Typography variant="caption" color="text.secondary">
              {wb.configVersions.length > 0
                ? `共 ${wb.versionPickerFiltered.length} 条${wb.versionPickerFiltered.length !== wb.configVersions.length ? `（已筛选，全部 ${wb.configVersions.length} 条）` : ''}`
                : '暂无可选版本'}
            </Typography>
            <List sx={{ maxHeight: 340, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: 1 }}>
              {wb.versionPickerSlice.length > 0 ? wb.versionPickerSlice.map((version) => (
                <ListItemButton
                  key={version.id}
                  selected={version.id === wb.selectedConfigVersion}
                  onClick={() => {
                    wb.closeVersionsDialog();
                    wb.requestApplyVersion(version.id);
                  }}
                >
                  <ListItemText
                    primary={version.id}
                    secondary={version.updatedAt || version.createdAt}
                  />
                </ListItemButton>
              )) : (
                <Box sx={{ p: 1.5 }}>
                  <Typography variant="body2" color="text.secondary">
                    {wb.configVersions.length > 0 ? '没有匹配的版本。' : '暂无可应用的工作台版本。'}
                  </Typography>
                </Box>
              )}
            </List>
            {wb.versionPickerFiltered.length > 8 ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', pt: 0.5 }}>
                <Pagination
                  count={wb.versionPickerTotalPages}
                  page={Math.min(wb.versionPickerPage, wb.versionPickerTotalPages)}
                  onChange={(_event, nextPage) => wb.setVersionPickerPage(nextPage)}
                  size="small"
                  color="primary"
                />
              </Box>
            ) : null}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={wb.closeVersionsDialog}>关闭</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default StrategyDesignMetaDialogs;
