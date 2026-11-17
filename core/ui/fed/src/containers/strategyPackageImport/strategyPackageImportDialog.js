import React, { useCallback, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import {
  FormControl,
  FormControlLabel,
  FormLabel,
  List,
  ListItem,
  ListItemText,
  Radio,
  RadioGroup,
  Stack,
  Typography,
} from '@mui/material';
import {
  importStrategyPackage,
  previewStrategyPackageImport,
} from 'api/strategyApi';
import { useAsyncAction } from 'service/useAsyncAction';
import { Button, Dialog, Message } from 'ui';
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
      <Stack spacing={2}>
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
          <Typography variant="body2" color="text.secondary">
            已选：
            {file.name}
          </Typography>
        ) : null}

        <FormControl>
          <FormLabel>冲突策略</FormLabel>
          <RadioGroup
            value={policy}
            onChange={(e) => {
              setPolicy(e.target.value);
              setPreview(null);
            }}
          >
            {POLICY_OPTIONS.map((opt) => (
              <FormControlLabel
                key={opt.value}
                value={opt.value}
                control={<Radio size="small" />}
                label={opt.label}
              />
            ))}
          </RadioGroup>
        </FormControl>

        {error ? <Message status="error">{error}</Message> : null}

        {preview?.items?.length ? (
          <Stack spacing={0.5}>
            <Typography variant="subtitle2">
              预览（
              {preview.ok ? '可导入' : '存在冲突'}
              ）
            </Typography>
            <List dense disablePadding>
              {preview.items.map((row) => (
                <ListItem key={`${row.kind}:${row.name}`} disableGutters>
                  <ListItemText
                    primary={`${row.kind} / ${row.name}`}
                    secondary={statusLabel(row.status)}
                  />
                </ListItem>
              ))}
            </List>
          </Stack>
        ) : null}
      </Stack>
    </Dialog>
  );
}

StrategyPackageImportDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func,
};

export default StrategyPackageImportDialog;
