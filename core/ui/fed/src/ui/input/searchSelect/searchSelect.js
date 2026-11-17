import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  InputAdornment,
  MenuItem,
  Popover,
  TextField as MuiTextField,
} from '@mui/material';
import NtqIcon from 'ui/icon/ntqIcon';
import Field from 'ui/input/field';
import InstantTransition from 'ui/input/instantTransition';
import useControlId from 'ui/input/useControlId';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import '../_control.scss';

function emitChange(onChange, name, next) {
  if (typeof onChange !== 'function') return;
  onChange({
    target: {
      name: name || undefined,
      value: next,
    },
  });
}

/**
 * 带搜索的下拉：触发器显示当前值；展开后面板内有搜索框过滤长列表。
 * onChange 与 Select 对齐：e.target.value（清空为 ''）。
 *
 * @example
 * <SearchSelect
 *   label="策略"
 *   value={v}
 *   onChange={(e) => setV(e.target.value)}
 *   options={[{ value: 'a', label: '动量增强' }]}
 *   placeholder="搜索策略…"
 * />
 */
function SearchSelect({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  required = false,
  name = '',
  id = '',
  value,
  onChange,
  options = [],
  placeholder = '搜索…',
  emptyLabel = '请选择',
  disabled = false,
  clearable = true,
  noOptionsText = '无匹配项',
  className = '',
  fullWidth = true,
  /** 默认限制约 280px；传 false 去掉上限 */
  maxWidth = true,
  ...rest
}) {
  const controlId = useControlId(id);
  const listId = `${controlId}-listbox`;
  const searchId = `${controlId}-search`;
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const list = useMemo(() => (Array.isArray(options) ? options : []), [options]);
  const hasFieldChrome = placement !== 'none' || tip || hint || error || label;
  const widthClass = maxWidth ? 'ntq-input--capped' : 'ntq-input--fluid';

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const anchorRef = useRef(null);
  const searchRef = useRef(null);

  const selected = useMemo(() => {
    if (value === '' || value === null || value === undefined) return null;
    return list.find((o) => String(o.value) === String(value)) || null;
  }, [list, value]);

  const filtered = useMemo(() => {
    const q = String(query || '').trim().toLowerCase();
    if (!q) return list;
    return list.filter((opt) => {
      const labelText = String(opt?.label ?? '').toLowerCase();
      const valueText = String(opt?.value ?? '').toLowerCase();
      return labelText.includes(q) || valueText.includes(q);
    });
  }, [list, query]);

  useEffect(() => {
    if (!open) return undefined;
    const t = window.setTimeout(() => {
      searchRef.current?.focus?.();
    }, 0);
    return () => window.clearTimeout(t);
  }, [open]);

  const handleOpen = () => {
    if (disabled) return;
    setQuery('');
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setQuery('');
  };

  const handlePick = (opt) => {
    if (opt?.disabled) return;
    emitChange(onChange, name, opt.value);
    handleClose();
  };

  const handleClear = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (disabled) return;
    emitChange(onChange, name, '');
  };

  const triggerLabel = selected
    ? (selected.label ?? String(selected.value))
    : emptyLabel;

  const control = (
    <div
      className={[
        'ntq-search-select',
        fullWidth ? 'ntq-search-select--fluid' : '',
        widthClass,
        open ? 'is-open' : '',
        disabled ? 'is-disabled' : '',
        error ? 'is-error' : '',
        !hasFieldChrome ? className : '',
      ].filter(Boolean).join(' ')}
      {...rest}
    >
      <button
        ref={anchorRef}
        id={controlId}
        type="button"
        className="ntq-search-select__trigger"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-label={placement === 'none' ? (label || emptyLabel) : undefined}
        onClick={() => (open ? handleClose() : handleOpen())}
      >
        <span
          className={[
            'ntq-search-select__value',
            selected ? '' : 'ntq-search-select__value--placeholder',
          ].filter(Boolean).join(' ')}
        >
          {triggerLabel}
        </span>
        <span className="ntq-search-select__actions">
          {clearable && selected && !disabled ? (
            <span
              className="ntq-search-select__clear"
              role="button"
              tabIndex={-1}
              aria-label="清除"
              onClick={handleClear}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') handleClear(e);
              }}
            >
              <NtqIcon name="cancel" size="sm" tone="muted" />
            </span>
          ) : null}
          <NtqIcon name="expandMore" size="sm" tone="muted" />
        </span>
      </button>

      <Popover
        open={open}
        anchorEl={anchorRef.current}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        TransitionComponent={InstantTransition}
        transitionDuration={0}
        disableScrollLock
        BackdropProps={{
          className: 'ntq-menu-backdrop',
          invisible: true,
        }}
        PaperProps={{
          className: 'ntq-search-select__paper',
          style: {
            width: anchorRef.current
              ? `${anchorRef.current.offsetWidth}px`
              : undefined,
            minWidth: '12rem',
          },
        }}
      >
        <div className="ntq-search-select__panel">
          <div className="ntq-search-select__search">
            <MuiTextField
              inputRef={searchRef}
              id={searchId}
              size="small"
              fullWidth
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              inputProps={{ 'aria-label': placeholder || '搜索' }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <NtqIcon name="search" size="sm" tone="muted" />
                  </InputAdornment>
                ),
              }}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  e.stopPropagation();
                  handleClose();
                }
              }}
            />
          </div>
          <ul
            id={listId}
            className="ntq-search-select__list"
            role="listbox"
            aria-label={label || emptyLabel}
          >
            {filtered.length === 0 ? (
              <li className="ntq-search-select__empty ntq-muted">{noOptionsText}</li>
            ) : (
              filtered.map((opt) => {
                const active = selected && String(selected.value) === String(opt.value);
                return (
                  <MenuItem
                    key={String(opt.value)}
                    component="li"
                    role="option"
                    aria-selected={active}
                    selected={active}
                    disabled={Boolean(opt.disabled)}
                    className="ntq-search-select__option"
                    onClick={() => handlePick(opt)}
                  >
                    {opt.label ?? String(opt.value)}
                  </MenuItem>
                );
              })
            )}
          </ul>
        </div>
      </Popover>
    </div>
  );

  if (!hasFieldChrome) {
    return control;
  }

  return (
    <Field
      label={label}
      labelPlacement={placement}
      tip={tip}
      hint={hint}
      error={error}
      htmlFor={controlId}
      required={required}
      bindControlId={false}
      className={[widthClass, className].filter(Boolean).join(' ')}
    >
      {control}
    </Field>
  );
}

export default SearchSelect;
