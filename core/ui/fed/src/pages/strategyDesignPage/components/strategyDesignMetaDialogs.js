import React from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Link,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Pagination,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import VersionPickLabel from 'components/versionPickLabel/versionPickLabel';
import VersionPinToggle from 'components/versionPickLabel/versionPinToggle';
import {
  SETTINGS_RETENTION_HREF,
  lookupVersionById,
  retentionCapFromVersions,
} from 'components/versionPickLabel/versionPickMarks';
import { formatVersionPickTime } from '../../../utils/formatDateTime';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

function StrategyDesignMetaDialogs() {
  const wb = useStrategyDesignWorkbenchContext();
  const pendingVersion = lookupVersionById(wb.configVersions, wb.pendingVersionId);
  const pendingDeleteVersion = lookupVersionById(wb.configVersions, wb.pendingDeleteVersionId);
  const retentionCap = retentionCapFromVersions(wb.configVersions);
  const pendingDeleteId = pendingDeleteVersion.id || wb.pendingDeleteVersionId;

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
          {pendingVersion.expiresSoon && !pendingVersion.pinned ? (
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
        <DialogTitle sx={{ pr: 3 }}>
          <Stack direction="row" alignItems="baseline" justifyContent="space-between" spacing={2}>
            <Box component="span" sx={{ flexShrink: 0 }}>恢复到历史版本</Box>
            <Typography
              variant="caption"
              color="text.secondary"
              component="div"
              sx={{ fontWeight: 400, textAlign: 'right', lineHeight: 1.4 }}
            >
              当前设置最多保留
              {' '}
              「
              <Box
                component="span"
                sx={{ fontWeight: 700, fontSize: '1.2em', color: 'text.primary' }}
              >
                {retentionCap > 0 ? retentionCap : '—'}
              </Box>
              」个版本
              {' · 已固定的不会自动清理 · '}
              <Link
                href={SETTINGS_RETENTION_HREF}
                target="_blank"
                rel="noopener noreferrer"
                underline="hover"
              >
                去设置
              </Link>
            </Typography>
          </Stack>
        </DialogTitle>
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
                <ListItem
                  key={version.id}
                  disablePadding
                  secondaryAction={(
                    <Stack direction="row" className="ntq-version-row-actions" alignItems="center">
                      <VersionPinToggle
                        version={version}
                        versions={wb.configVersions}
                        disabled={wb.disablePinActions}
                        onToggle={wb.toggleVersionPinned}
                      />
                      <IconButton
                        size="small"
                        color="error"
                        className="ntq-version-row-action ntq-version-row-action--danger"
                        aria-label={`删除 ${version.id}`}
                        title="删除此版本产物"
                        disabled={wb.disableMetaActions || wb.isDeletingVersion}
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          wb.requestDeleteVersion(version.id);
                        }}
                      >
                        <NtqIcon name="trash" size={20} tone="error" />
                      </IconButton>
                    </Stack>
                  )}
                >
                  <ListItemButton
                    selected={version.id === wb.selectedConfigVersion}
                    sx={{ pr: 14 }}
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
                </ListItem>
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
        open={wb.deleteConfirmOpen}
        onClose={() => {
          if (!wb.isDeletingVersion) wb.setDeleteConfirmOpen(false);
        }}
        maxWidth="xs"
        fullWidth
        sx={{ zIndex: (theme) => theme.zIndex.modal + 2 }}
      >
        <DialogTitle>确认删除 {pendingDeleteId}？</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2">
            将永久删除这份回测的报告、缓存目录和版本登记，删除后无法恢复。
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            不会改 settings.py，也不会改当前编辑器里的配置。
          </Typography>
          {pendingDeleteVersion.pinned ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              该版本已固定。固定只跳过自动清理，仍可以手动删除。
            </Typography>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => wb.setDeleteConfirmOpen(false)}
            disabled={wb.isDeletingVersion}
          >
            取消
          </Button>
          <Button
            variant="contained"
            color="error"
            disabled={wb.isDeletingVersion}
            onClick={wb.confirmDeleteVersion}
          >
            {wb.isDeletingVersion ? '删除中...' : '确认删除'}
          </Button>
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
