import React from 'react';
import './style.scss';

/**
 * 列表页工具条：左侧搜索（可选）+ 右侧操作按钮槽 + 可选尾部提示。
 *
 * @example
 * <ListToolbar
 *   search={(
 *     <SearchField fluid surface="glass" label="搜索" value={q} onChange={…} />
 *   )}
 *   actions={(
 *     <>
 *       <Button variant="glass" icon="refresh" onClick={load}>刷新</Button>
 *       <Button variant="primary" icon="add">新建</Button>
 *     </>
 *   )}
 *   hint="一次仅允许扫描一个策略"
 * />
 */
function ListToolbar({
  search = null,
  actions = null,
  hint = null,
  className = '',
}) {
  const rootClass = ['ntq-list-toolbar', className].filter(Boolean).join(' ');
  const hasHint = hint != null && hint !== false && hint !== '';

  return (
    <div className={rootClass}>
      {search != null && search !== false ? (
        <div className="ntq-list-toolbar__search">{search}</div>
      ) : null}
      {actions != null && actions !== false ? (
        <div className="ntq-list-toolbar__actions">{actions}</div>
      ) : null}
      {hasHint ? (
        <div className="ntq-list-toolbar__hint ntq-muted">{hint}</div>
      ) : null}
    </div>
  );
}

export default ListToolbar;
