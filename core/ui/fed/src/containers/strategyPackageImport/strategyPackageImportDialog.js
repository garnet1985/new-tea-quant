import React, { useCallback, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import {
  importStrategyPackage,
  previewStrategyPackageImport,
} from 'api/strategyApi';
import { useAsyncAction } from 'service/useAsyncAction';
import { Button, Dialog, Message, RadioGroup } from 'ui';
import './style.scss';

const POLICY_OPTIONS = [
  { value: 'reject', label: '重名拒绝' },
  { value: 'skip_existing', label: '跳过已存在' },
  { value: 'overwrite', label: '覆盖已存在' },
];

function statusLabel(status) {
  if (status === 'will_install') return '将安装';
  if (status === 'exists_skip') return '跳过（已存在）';
  if (status === 'conflict') return '冲突';
  return status || '—';
}

function StrategyPackageImportDialog({ open, onClose, onSuccess = null }) {
  const [file, setFile] = useState(null);
  const [policy, setPolicy] = useState('reject');
  const [preview, setPreview] = useState(null);

  const previewAction = useAsyncAction(
    useCallback(
      ({ importFile, importPolicy }) => previewStrategyPackageImport(importFile, { policy: importPolicy }),
      [],
    ),
  );
  const importAction = useAsyncAction(
    useCallback(
      ({ importFile, importPolicy }) => importStrategyPackage(importFile, { policy: importPolicy }),
      [],
    ),
  );

  const busy = previewAction.busy || importAction.busy;
  const error = previewAction.error || importAction.error;
  const { clearError: clearPreviewError } = previewAction;
  const { clearError: clearImportError } = importAction;

  useEffect(() => {
    if (!open) {
      setFile(null);
      setPolicy('reject');
      setPreview(null);
      clearPreviewError();
      clearImportError();
    }
  }, [open, clearPreviewError, clearImportError]);

  const handleFileChange = (event) => {
    setFile(event.target.files?.[0] || null);
    setPreview(null);
    clearPreviewError();
    clearImportError();
  };

  const handlePreview = async () => {
    if (!file) return;
    try {
      const result = await previewAction.run({ importFile: file, importPolicy: policy });
      setPreview(result);
    } catch {
      setPreview(null);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    try {
      const result = await importAction.run({ importFile: file, importPolicy: policy });
      onSuccess?.(result);
      onClose();
    } catch (e) {
      if (e?.preview) setPreview(e.preview);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={busy ? undefined : onClose}
      title="导入策略包"
      size="sm"
      className="strategy-package-import-dialog"
      actions={(
        <div className="strategy-package-import-dialog__actions">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={busy}
            className="strategy-package-import-dialog__btn"
          >
            取消
          </Button>
          <Button
            variant="glass"
            onClick={handlePreview}
            disabled={!file || busy}
            className="strategy-package-import-dialog__btn"
          >
            预览
          </Button>
          <Button
            variant="primary"
            onClick={handleImport}
            disabled={!file || busy}
            className="strategy-package-import-dialog__btn strategy-package-import-dialog__btn--primary"
          >
            导入策略包
          </Button>
        </div>
      )}
    >
      <div className="strategy-package-import-dialog__body">
        <p className="ntq-muted">
          仅支持策略交流包（策略目录及依赖的 tag / adapter），文件格式为 .zip。
        </p>
        <Button
          variant="glass"
          component="label"
          disabled={busy}
          className="strategy-package-import-dialog__file"
        >
          选择策略包文件
          <input type="file" accept=".zip,application/zip" hidden onChange={handleFileChange} />
        </Button>
        {file ? (
          <p className="ntq-muted">
            已选：
            {file.name}
          </p>
        ) : null}

        <RadioGroup
          label="冲突策略"
          options={POLICY_OPTIONS}
          value={policy}
          disabled={busy}
          onChange={(e) => {
            setPolicy(e.target.value);
            setPreview(null);
          }}
        />

        {error ? <Message status="error">{error}</Message> : null}

        {preview?.items?.length ? (
          <div className="strategy-package-import-dialog__preview">
            <h4 className="strategy-package-import-dialog__preview-title">
              预览（
              {preview.ok ? '可导入' : '存在冲突'}
              ）
            </h4>
            <ul className="strategy-package-import-dialog__list">
              {preview.items.map((row) => (
                <li key={`${row.kind}:${row.name}`} className="strategy-package-import-dialog__item">
                  <span className="strategy-package-import-dialog__item-name">
                    {`${row.kind} / ${row.name}`}
                  </span>
                  <span className="strategy-package-import-dialog__item-status ntq-muted">
                    {statusLabel(row.status)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </Dialog>
  );
}

StrategyPackageImportDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func,
};

export default StrategyPackageImportDialog;
