import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Button,
  CategoryChipStrip,
  CountBadge,
  DataGrid,
  Icon,
  ListToolbar,
  Loading,
  Message,
  SearchField,
  Section,
  Tag,
} from 'ui';
import { showToast } from 'ui/message/toast';
import { PageLayout } from 'ntq-ui';
import {
  downloadStrategyPackage,
  fetchStrategyList,
  getStrategyDesignPath,
  getStrategyDisplayLabel,
} from '../../api/strategyApi';
import {
  groupStrategiesByCategory,
  readStrategyListCategoryQuery,
  STRATEGY_LIST_CATEGORY_PARAM,
} from 'containers/strategyCategory';
import StrategyPackageImportDialog from '../../containers/strategyPackageImport';
import DescriptionText from 'ntq-ui/descriptionText';
import { buildStrategyDesignNavState } from 'containers/strategyDesign';
import './strategyListPage.scss';

/**
 * @param {object} props
 * @param {string} [props.listBasePath] 列表页路由（面包屑）
 * @param {(name: string) => string} [props.getEnterPath] 进入单策略调试页
 * @param {string} [props.navLabel] 主导航/面包屑标签
 * @param {string} [props.bannerTitle]
 * @param {string} [props.bannerDescription]
 */
const STRATEGY_LIST_BANNER_TITLE = '选择一个策略';
const STRATEGY_LIST_BANNER_DESCRIPTION =
  '管理本地策略，进行参数调试与分步回测。';

function StrategyListPage({
  listBasePath = '/strategy-design',
  getEnterPath = getStrategyDesignPath,
  navLabel = '制定策略',
  bannerTitle = STRATEGY_LIST_BANNER_TITLE,
  bannerDescription = STRATEGY_LIST_BANNER_DESCRIPTION,
}) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [nameQuery, setNameQuery] = useState('');
  const [importOpen, setImportOpen] = useState(false);
  const [exportingName, setExportingName] = useState('');

  const categoryQuery = readStrategyListCategoryQuery(searchParams);
  const selectedChipRef = useRef(null);

  const catalogGroups = useMemo(
    () => groupStrategiesByCategory(rows),
    [rows],
  );

  const categoryFilteredRows = useMemo(() => {
    if (!categoryQuery) return rows;
    const match = catalogGroups.find((g) => g.queryValue === categoryQuery);
    return match ? match.rows : [];
  }, [rows, categoryQuery, catalogGroups]);

  const catalogHasSelectedCategory = Boolean(
    !categoryQuery || catalogGroups.some((g) => g.queryValue === categoryQuery),
  );

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return categoryFilteredRows;
    return categoryFilteredRows.filter((r) => {
      const id = String(r.name || '').toLowerCase();
      const path = String(r.path || '').toLowerCase();
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      const desc = String(r.description || '').toLowerCase();
      const category = String(r.category || '').toLowerCase();
      return (
        id.includes(q)
        || path.includes(q)
        || key.includes(q)
        || label.includes(q)
        || desc.includes(q)
        || category.includes(q)
      );
    });
  }, [categoryFilteredRows, nameQuery]);

  const groupedRows = useMemo(
    () => groupStrategiesByCategory(displayRows),
    [displayRows],
  );

  const setCategoryQuery = useCallback((nextQuery) => {
    const q = String(nextQuery || '').trim();
    if (q === categoryQuery) return;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (q) next.set(STRATEGY_LIST_CATEGORY_PARAM, q);
      else next.delete(STRATEGY_LIST_CATEGORY_PARAM);
      return next;
    });
  }, [categoryQuery, setSearchParams]);

  const toggleCategoryQuery = useCallback((queryValue) => {
    const q = String(queryValue || '').trim();
    setCategoryQuery(q && q === categoryQuery ? '' : q);
  }, [categoryQuery, setCategoryQuery]);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    fetchStrategyList()
      .then((res) => {
        setRows(res.data);
      })
      .catch((e) => {
        setLoadError(e?.message || '加载失败');
        setRows([]);
      })
      .finally(() => {
        setLoading(false);
        setPageReady(true);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    selectedChipRef.current?.scrollIntoView({
      behavior: 'smooth',
      inline: 'nearest',
      block: 'nearest',
    });
  }, [categoryQuery]);

  const handleExportStrategyPackage = useCallback(async (strategyName) => {
    if (!strategyName || exportingName) return;
    setExportingName(strategyName);
    try {
      await downloadStrategyPackage(strategyName, { scope: 'bundle' });
    } catch (e) {
      showToast({ status: 'error', content: e?.message || '导出失败' });
    } finally {
      setExportingName('');
    }
  }, [exportingName]);

  const enterNavState = useCallback((row) => buildStrategyDesignNavState(row), []);

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '策略名',
      minWidth: 160,
      flex: 0.5,
      valueGetter: (params) => getStrategyDisplayLabel(params.row),
      renderCell: (params) => (
        <RouterLink
          to={getEnterPath(params.row.name)}
          state={enterNavState(params.row)}
          className="strategy-list-name-link"
          onClick={(e) => e.stopPropagation()}
        >
          {params.value || params.row.name}
        </RouterLink>
      ),
    },
    {
      field: 'is_enabled',
      headerName: '状态',
      width: 110,
      renderCell: (params) => (params.value ? (
        <Tag status="success" variant="solid">已启用</Tag>
      ) : (
        <Tag status="neutral" variant="outline">已禁用</Tag>
      )),
    },
    {
      field: 'actions',
      headerName: '操作',
      width: 220,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const name = params.row.name;
        const exportId = params.row.key || name;
        const isExporting = exportingName === exportId;
        const exportBusy = Boolean(exportingName);
        return (
          <div
            className="strategy-list-cell-actions"
            data-ntq-help="strategy-list-enter"
          >
            <RouterLink
              to={getEnterPath(name)}
              state={enterNavState(params.row)}
              className="ntq-link strategy-list-enter"
              onClick={(e) => e.stopPropagation()}
            >
              进入制定
              <Icon name="chevronRight" size="sm" />
            </RouterLink>
            <span className="strategy-list-actions-sep" aria-hidden>|</span>
            <button
              type="button"
              className="ntq-link strategy-list-export"
              disabled={exportBusy}
              onClick={(e) => {
                e.stopPropagation();
                handleExportStrategyPackage(exportId);
              }}
            >
              {isExporting ? '导出中…' : '导出'}
            </button>
          </div>
        );
      },
    },
    {
      field: 'description',
      headerName: '描述',
      minWidth: 240,
      flex: 1.5,
      sortable: false,
      renderCell: (params) => (
        <DescriptionText
          text={params.value}
          className="strategy-list-desc ntq-muted"
          empty="—"
          maxLines={3}
        />
      ),
    },
  ]), [enterNavState, exportingName, getEnterPath, handleExportStrategyPackage]);

  return (
    <PageLayout
      className="strategy-list-page"
      breadcrumbsItems={[{ label: navLabel, to: listBasePath }]}
      breadcrumbsCurrent="选择一个策略"
      bannerTitle={bannerTitle}
      bannerDescription={bannerDescription}
      loading={!pageReady}
      loadingMessage="正在加载策略列表…"
    >
      <Section className="strategy-list-page__stack" gap="md">
        {loadError ? <Message status="error">{loadError}</Message> : null}

        <Section className="strategy-list-grid" gap="md">
          <ListToolbar
            search={(
              <SearchField
                fluid
                surface="glass"
                placeholder="输入策略名称搜索"
                label="按策略名搜索"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
              />
            )}
            actions={(
              <div
                className="strategy-list-toolbar-actions"
                data-ntq-help="strategy-list-refresh-import"
              >
                <Button
                  variant="glass"
                  icon="refresh"
                  onClick={load}
                  disabled={loading}
                >
                  刷新策略
                </Button>
                <Button
                  variant="primary"
                  icon="uploadFile"
                  onClick={() => setImportOpen(true)}
                  disabled={loading}
                >
                  导入策略包
                </Button>
              </div>
            )}
          />

          {catalogGroups.length > 0 ? (
            <div data-ntq-help="strategy-list-filter">
              <CategoryChipStrip
                all={{
                  label: '全部',
                  count: rows.length,
                  selected: !categoryQuery,
                  onClick: () => setCategoryQuery(''),
                }}
                items={catalogGroups.map(({ category, queryValue, rows: categoryRows }) => ({
                  key: queryValue,
                  label: category,
                  count: categoryRows.length,
                  title: category,
                  selected: categoryQuery === queryValue,
                  onClick: () => toggleCategoryQuery(queryValue),
                }))}
                selectedItemRef={selectedChipRef}
              />
            </div>
          ) : null}

          <div
            className={[
              'strategy-list-grid-body',
              loading && rows.length === 0 ? 'strategy-list-grid-body--loading' : '',
            ].filter(Boolean).join(' ')}
          >
            {loading && rows.length === 0 ? (
              <Loading variant="inline" message="正在加载策略列表…" />
            ) : !loading && categoryQuery && !catalogHasSelectedCategory ? (
              <p className="ntq-muted strategy-list-category-empty">没有该归类的策略</p>
            ) : groupedRows.length === 0 ? (
              <p className="ntq-muted strategy-list-category-empty">
                {nameQuery.trim() ? '没有匹配的策略' : '暂无策略'}
              </p>
            ) : (
              <div className="strategy-list-category-stack">
                {groupedRows.map(({ category, queryValue, rows: categoryRows }, index) => (
                  <div
                    key={queryValue}
                    className="strategy-list-category-section"
                    data-ntq-help={index === 0 ? 'strategy-list-table' : undefined}
                  >
                    <div className="strategy-list-category">
                      <button
                        type="button"
                        className="strategy-list-category-header-btn"
                        onClick={() => toggleCategoryQuery(queryValue)}
                        aria-pressed={categoryQuery === queryValue}
                        title={categoryQuery === queryValue ? '显示全部归类' : `只看${category}`}
                      >
                        <span className="strategy-list-category-header-label">{category}</span>
                        <CountBadge
                          count={categoryRows.length}
                          label={`${categoryRows.length} 个策略`}
                        />
                      </button>
                    </div>
                    <DataGrid
                      autoHeight
                      rows={categoryRows}
                      columns={columns}
                      loading={false}
                      getRowHeight={() => 'auto'}
                      cellLayout="wrap"
                      hideFooter
                      className="strategy-list-data-grid"
                      onRowDoubleClick={(params) => {
                        navigate(getEnterPath(params.row.name), {
                          state: enterNavState(params.row),
                        });
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </Section>
      </Section>

      <StrategyPackageImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={(result) => {
          const name = result?.strategy_name || '策略包';
          showToast({ status: 'success', content: `已导入 ${name}，列表已刷新` });
          load();
        }}
      />
    </PageLayout>
  );
}

export default StrategyListPage;
