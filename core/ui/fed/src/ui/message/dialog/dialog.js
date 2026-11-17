import React from 'react';
import {
  Dialog as MuiDialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from '@mui/material';
import { pickToken } from 'ui/tokens';
import './style.scss';

/** 图鉴 / API：sm 窄确认、md 说明、lg 较宽表单 */
const DIALOG_SIZES = ['sm', 'md', 'lg'];
const SIZE_TO_MUI = {
  sm: 'xs',
  md: 'sm',
  lg: 'md',
};

/**
 * 模态对话框（确认 / 说明弹层）。
 * MUI Dialog 仅作内部实现；页面只消费本组件。
 *
 * @example
 * <Dialog
 *   open={open}
 *   onClose={() => setOpen(false)}
 *   title="确认清理？"
 *   actions={(
 *     <>
 *       <Button variant="ghost" onClick={() => setOpen(false)}>取消</Button>
 *       <Button variant="danger" onClick={onConfirm}>确认</Button>
 *     </>
 *   )}
 * >
 *   <p className="ntq-muted">此操作不可撤销。</p>
 * </Dialog>
 */
function Dialog({
  open = false,
  onClose,
  title = '',
  children = null,
  actions = null,
  size = 'sm',
  disableEscapeKeyDown = false,
  className = '',
  ...rest
}) {
  const sizeToken = pickToken(size, DIALOG_SIZES, 'sm');
  const rootClass = ['ntq-dialog', className].filter(Boolean).join(' ');

  return (
    <MuiDialog
      open={Boolean(open)}
      onClose={onClose}
      maxWidth={SIZE_TO_MUI[sizeToken]}
      fullWidth
      disableEscapeKeyDown={disableEscapeKeyDown}
      className={rootClass}
      classes={{ paper: 'ntq-dialog__paper' }}
      {...rest}
    >
      {title ? (
        <DialogTitle className="ntq-dialog__title">{title}</DialogTitle>
      ) : null}
      {children != null && children !== false ? (
        <DialogContent className="ntq-dialog__content">
          {children}
        </DialogContent>
      ) : null}
      {actions ? (
        <DialogActions className="ntq-dialog__actions">
          {actions}
        </DialogActions>
      ) : null}
    </MuiDialog>
  );
}

export default Dialog;
export { DIALOG_SIZES };
