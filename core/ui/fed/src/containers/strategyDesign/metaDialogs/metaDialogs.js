import React from 'react';
import { Button, Dialog } from 'ui';
import {
  VersionPickerDialog,
  SETTINGS_RETENTION_HREF,
  lookupVersionById,
  retentionCapFromVersions,
} from 'containers/versionPick';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import './style.scss';

function StrategyDesignMetaDialogs() {
  const wb = useStrategyDesignWorkbenchContext();
  const pendingVersion = lookupVersionById(wb.configVersions, wb.pendingVersionId);
  const pendingDeleteVersion = lookupVersionById(wb.configVersions, wb.pendingDeleteVersionId);
  const retentionCap = retentionCapFromVersions(wb.configVersions);
  const pendingDeleteId = pendingDeleteVersion.id || wb.pendingDeleteVersionId;

  return (
    <>
      <Dialog
        open={wb.confirmOpen}
        onClose={() => wb.setConfirmOpen(false)}
        title="恢复历史版本配置"
        size="sm"
        actions={(
          <>
            <Button variant="ghost" onClick={() => wb.setConfirmOpen(false)}>
              取消
            </Button>
            <Button
              variant="primary"
              disabled={wb.isSavingSettings}
              onClick={wb.confirmRestoreVersion}
            >
              {wb.isSavingSettings ? '处理中...' : '确认恢复'}
            </Button>
          </>
        )}
      >
        <p>
          将把版本
          {' '}
          <strong>{wb.pendingVersionId}</strong>
          {' '}
          当时冻结的配置写回 settings.py，并刷新当前编辑器。未保存的草稿将被覆盖。
        </p>
        {pendingVersion.envInvalid ? (
          <p className="ntq-muted">
            该版本产物仅供查阅。恢复配置后运行会按当前环境查找或新建 version，不会写回此目录。
          </p>
        ) : null}
        {pendingVersion.expiresSoon ? (
          <p className="ntq-muted">
            该版本所在的过时环境已接近保留上限，下次再出现新环境时可能整组被清理。恢复配置不受影响。
          </p>
        ) : null}
      </Dialog>

      <VersionPickerDialog
        open={wb.moreVersionsOpen}
        onClose={wb.closeVersionsDialog}
        title="恢复到历史版本"
        titleExtra={(
          <div className="ntq-meta-dialogs__retention ntq-muted">
            当前设置最多保留
            {' '}
            「
            <span className="ntq-meta-dialogs__retention-cap">
              {retentionCap > 0 ? retentionCap : '—'}
            </span>
            」组过时环境
            {' · '}
            <a
              className="ntq-link"
              href={SETTINGS_RETENTION_HREF}
              target="_blank"
              rel="noopener noreferrer"
            >
              去设置
            </a>
          </div>
        )}
        versions={wb.configVersions}
        selectedId={wb.selectedConfigVersion}
        emptyHint="暂无可应用的工作台版本。"
        onSelect={(versionId) => wb.requestApplyVersion(versionId)}
        renderSecondaryAction={(version) => (
          <div className="ntq-version-row-actions">
            <Button
              variant="ghost"
              icon="trash"
              className="ntq-version-row-action ntq-version-row-action--danger"
              aria-label={`删除 ${version.id}`}
              tooltip="删除此版本产物"
              disabled={wb.disableMetaActions || wb.isDeletingVersion}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                wb.requestDeleteVersion(version.id);
              }}
            />
          </div>
        )}
      />

      <Dialog
        open={wb.deleteConfirmOpen}
        onClose={() => {
          if (!wb.isDeletingVersion) wb.setDeleteConfirmOpen(false);
        }}
        title={`确认删除 ${pendingDeleteId}？`}
        size="sm"
        sx={{ zIndex: (theme) => theme.zIndex.modal + 2 }}
        actions={(
          <>
            <Button
              variant="ghost"
              onClick={() => wb.setDeleteConfirmOpen(false)}
              disabled={wb.isDeletingVersion}
            >
              取消
            </Button>
            <Button
              variant="danger"
              disabled={wb.isDeletingVersion}
              onClick={wb.confirmDeleteVersion}
            >
              {wb.isDeletingVersion ? '删除中...' : '确认删除'}
            </Button>
          </>
        )}
      >
        <p>
          将永久删除这份回测的报告、缓存目录和版本登记，删除后无法恢复。
        </p>
        <p className="ntq-muted">
          不会改 settings.py，也不会改当前编辑器里的配置。
        </p>
      </Dialog>

      <Dialog
        open={Boolean(wb.diskConflict)}
        onClose={() => {
          if (!wb.diskConflictBusy) wb.closeDiskConflict();
        }}
        title="文件已更新"
        size="sm"
        actions={(
          <>
            <Button
              variant="ghost"
              onClick={wb.closeDiskConflict}
              disabled={wb.diskConflictBusy}
            >
              取消
            </Button>
            <Button
              variant="glass"
              onClick={wb.confirmDiskConflictTakeFile}
              disabled={wb.diskConflictBusy}
            >
              用文件覆盖编辑器
            </Button>
            <Button
              variant="primary"
              onClick={wb.confirmDiskConflictOverwriteFile}
              disabled={wb.diskConflictBusy}
            >
              {wb.diskConflictBusy
                ? '处理中...'
                : (wb.diskConflict?.intent === 'restore' ? '仍要恢复历史版本' : '用编辑器覆盖文件')}
            </Button>
          </>
        )}
      >
        <p>
          settings.py 已在别处修改，与当前编辑器草稿不一致。
        </p>
        {wb.diskConflict?.intent === 'restore' ? (
          <p className="ntq-muted">
            继续恢复会丢掉当前草稿，并用历史版本覆盖磁盘上的新改动。
          </p>
        ) : null}
        {wb.diskConflict?.intent === 'run' ? (
          <p className="ntq-muted">
            用编辑器覆盖文件后才会继续运行。
          </p>
        ) : null}
      </Dialog>
    </>
  );
}

export default StrategyDesignMetaDialogs;
