import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
} from '../../api/apis/strategyApi';
import './strategyPackageImportDialog.scss';

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

function StrategyPackageImportDialog({ open, onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [policy, setPolicy] = useState('reject');
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) {
      setFile(null);
      setPolicy('reject');
      setPreview(null);
      setError(null);
      setBusy(false);
    }
  }, [open]);

  const handleFileChange = (event) => {
    setFile(event.target.files?.[0] || null);
    setPreview(null);
    setError(null);
  };

  const handlePreview = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await previewStrategyPackageImport(file, { policy });
      setPreview(result);
    } catch (e) {
      setPreview(null);
      setError(e?.message || '预览失败');
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await importStrategyPackage(file, { policy });
      onSuccess?.(result);
      onClose();
    } catch (e) {
      if (e?.preview) setPreview(e.preview);
      setError(e?.message || '导入失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={busy ? undefined : onClose}
      maxWidth="sm"
      fullWidth
      className="strategy-package-import-dialog"
    >
      <DialogTitle>导入策略包</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            仅支持策略交流包（策略目录及依赖的 tag / adapter），文件格式为 .zip。
          </Typography>
          <Button
            variant="outlined"
            component="label"
            disabled={busy}
            className="ntq-glass-outline-btn"
            sx={{ alignSelf: 'flex-start' }}
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

          {error ? <Alert severity="error">{error}</Alert> : null}

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
      </DialogContent>
      <DialogActions className="strategy-package-import-dialog__actions">
        <Button
          variant="text"
          size="small"
          onClick={onClose}
          disabled={busy}
          className="strategy-package-import-dialog__btn strategy-package-import-dialog__btn--ghost"
        >
          取消
        </Button>
        <Button
          variant="outlined"
          size="small"
          onClick={handlePreview}
          disabled={!file || busy}
          className="strategy-package-import-dialog__btn ntq-glass-outline-btn"
        >
          预览
        </Button>
        <Button
          variant="contained"
          color="primary"
          size="small"
          onClick={handleImport}
          disabled={!file || busy}
          className="strategy-package-import-dialog__btn strategy-package-import-dialog__btn--primary ntq-cyan-fill-btn"
        >
          导入策略包
        </Button>
      </DialogActions>
    </Dialog>
  );
}

StrategyPackageImportDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func,
};

StrategyPackageImportDialog.defaultProps = {
  onSuccess: null,
};

export default StrategyPackageImportDialog;
