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
import VersionPickLabel from 'components/versionPickLabel/versionPickLabel';
import { lookupVersionById } from 'components/versionPickLabel/versionPickMarks';
import { formatVersionPickTime } from '../../../utils/formatDateTime';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

function StrategyDesignMetaDialogs() {
  const wb = useStrategyDesignWorkbenchContext();
  const pendingVersion = lookupVersionById(wb.configVersions, wb.pendingVersionId);

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
          {pendingVersion.envInvalid ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              该版本产物仅供查阅。恢复配置后运行会按当前环境查找或新建 version，不会写回此目录。
            </Typography>
          ) : null}
          {pendingVersion.expiresSoon ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              该版本在保留额度触顶后会优先被清理。恢复配置不受影响。
            </Typography>
          ) : null}
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
        <DialogTitle>恢复到历史版本</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1}>
            <TextField
              size="small"
              fullWidth
              placeholder="搜索版本 ID、时间或标记"
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
                    primary={<VersionPickLabel version={version} />}
                    secondary={formatVersionPickTime(version)}
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
      <Dialog
        open={Boolean(wb.diskConflict)}
        onClose={() => {
          if (!wb.diskConflictBusy) wb.closeDiskConflict();
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>文件已更新</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2">
            settings.py 已在别处修改，与当前编辑器草稿不一致。
          </Typography>
          {wb.diskConflict?.intent === 'restore' ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              继续恢复会丢掉当前草稿，并用历史版本覆盖磁盘上的新改动。
            </Typography>
          ) : null}
          {wb.diskConflict?.intent === 'run' ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              用编辑器覆盖文件后才会继续运行。
            </Typography>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={wb.closeDiskConflict}
            disabled={wb.diskConflictBusy}
          >
            取消
          </Button>
          <Button
            onClick={wb.confirmDiskConflictTakeFile}
            disabled={wb.diskConflictBusy}
          >
            用文件覆盖编辑器
          </Button>
          <Button
            variant="contained"
            onClick={wb.confirmDiskConflictOverwriteFile}
            disabled={wb.diskConflictBusy}
          >
            {wb.diskConflictBusy
              ? '处理中...'
              : (wb.diskConflict?.intent === 'restore' ? '仍要恢复历史版本' : '用编辑器覆盖文件')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default StrategyDesignMetaDialogs;
