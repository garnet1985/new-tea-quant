import React, { useEffect, useMemo, useState } from 'react';
import { Button, Dialog, TextField } from 'ui';
import VersionPickLabel from './versionPickLabel';
import { versionPickSearchText } from './versionPickMarks';
import { formatVersionPickTime } from 'service/format/formatDateTime';
import './style.scss';

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

  const dialogTitle = (
    <div className="ntq-version-picker-dialog__title">
      <span className="ntq-version-picker-dialog__title-main">{title}</span>
      {titleExtra || null}
    </div>
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={dialogTitle}
      size="sm"
      sx={dialogSx}
      actions={(
        <Button variant="ghost" onClick={onClose}>关闭</Button>
      )}
    >
      <div className="ntq-version-picker-dialog__body">
        <TextField
          labelPlacement="none"
          maxWidth={false}
          placeholder="搜索版本 ID、时间或标记"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <p className="ntq-version-picker-dialog__meta">
          {pool.length > 0
            ? `共 ${filtered.length} 条${filtered.length !== pool.length ? `（已筛选，全部 ${pool.length} 条）` : ''}`
            : emptyHint}
        </p>
        <ul className="ntq-version-picker-dialog__list">
          {allowClear ? (
            <li className="ntq-version-picker-dialog__item">
              <button
                type="button"
                className={[
                  'ntq-version-picker-dialog__row',
                  !selected ? 'is-selected' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => pick('')}
              >
                <span className="ntq-version-picker-dialog__primary">{clearLabel}</span>
              </button>
            </li>
          ) : null}
          {slice.length > 0 ? slice.map((version) => (
            <li key={version.id} className="ntq-version-picker-dialog__item">
              <button
                type="button"
                className={[
                  'ntq-version-picker-dialog__row',
                  hasActions ? 'has-secondary' : '',
                  version.id === selected ? 'is-selected' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => pick(version.id)}
              >
                <span className="ntq-version-picker-dialog__primary">
                  <VersionPickLabel version={version} />
                </span>
                <span className="ntq-version-picker-dialog__secondary">
                  {formatVersionPickTime(version)}
                </span>
              </button>
              {hasActions ? (
                <div className="ntq-version-picker-dialog__secondary-action">
                  {renderSecondaryAction(version)}
                </div>
              ) : null}
            </li>
          )) : null}
          {slice.length === 0 && !(allowClear && pool.length === 0) ? (
            <li className="ntq-version-picker-dialog__empty">
              <p>{pool.length > 0 ? noMatchHint : emptyHint}</p>
            </li>
          ) : null}
        </ul>
        {filtered.length > VERSION_PICKER_PAGE_SIZE ? (
          <div className="ntq-version-picker-dialog__pages">
            <Button
              variant="ghost"
              disabled={currentPage <= 1}
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            >
              上一页
            </Button>
            <span className="ntq-version-picker-dialog__page-label">
              {currentPage} / {totalPages}
            </span>
            <Button
              variant="ghost"
              disabled={currentPage >= totalPages}
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
            >
              下一页
            </Button>
          </div>
        ) : null}
      </div>
    </Dialog>
  );
}

export default VersionPickerDialog;
