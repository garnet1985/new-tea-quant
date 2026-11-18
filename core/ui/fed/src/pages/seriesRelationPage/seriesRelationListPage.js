import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Button,
  DataGrid,
  Dialog,
  ListToolbar,
  Message,
  SearchField,
  Section,
  Tag,
  TextField,
} from 'ui';
import { showToast } from 'ui/message/toast';
import { PageLayout } from 'ntq-ui';
import {
  fetchSeriesRelationList,
  getSeriesRelationPath,
} from 'api/seriesRelationApi';
import './seriesRelationPage.scss';

function SeriesRelationListPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageReady, setPageReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [nameQuery, setNameQuery] = useState('');
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });

  const [newOpen, setNewOpen] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newDisplayName, setNewDisplayName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setLoadError('');
    fetchSeriesRelationList({ page: 1, limit: 500 })
      .then((res) => {
        setRows(
          (res.data || []).map((item) => ({
            ...item,
            id: item.key,
          })),
        );
      })
      .catch((err) => {
        setRows([]);
        setLoadError(err?.message || '加载序列关系列表失败');
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
    setPaginationModel((m) => ({ ...m, page: 0 }));
  }, [nameQuery]);

  const displayRows = useMemo(() => {
    const q = nameQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const key = String(r.key || '').toLowerCase();
      const label = String(r.display_name || '').toLowerCase();
      return key.includes(q) || label.includes(q);
    });
  }, [rows, nameQuery]);

  const enterScene = useCallback((key, state) => {
    if (!key) return;
    navigate(getSeriesRelationPath(key), { state: state || undefined });
  }, [navigate]);

  const confirmNew = () => {
    const key = String(newKey || '').trim();
    if (!key) {
      showToast({ status: 'error', content: '请填写场景 key' });
      return;
    }
    setNewOpen(false);
    enterScene(key, {
      isNew: true,
      display_name: String(newDisplayName || '').trim() || key,
    });
  };

  const columns = useMemo(() => ([
    {
      field: 'display_name',
      headerName: '名称',
      minWidth: 200,
      flex: 0.5,
      renderCell: (params) => (
        <RouterLink
          to={getSeriesRelationPath(params.row.key)}
          className="ntq-srel-list-link"
        >
          {params.value || params.row.key}
        </RouterLink>
      ),
    },
    {
      field: 'key',
      headerName: 'Key',
      minWidth: 180,
      flex: 0.4,
      renderCell: (params) => (
        <span className="ntq-srel-list-key ntq-muted">{params.value}</span>
      ),
    },
    {
      field: 'has_results',
      headerName: '结果',
      width: 110,
      renderCell: (params) => (
        // 约定：有结果（满足）solid；未跑批（未满足）outline
        params.value ? (
          <Tag status="success" variant="solid">有结果</Tag>
        ) : (
          <Tag status="neutral" variant="outline">未跑批</Tag>
        )
      ),
    },
    {
      field: 'actions',
      headerName: '',
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Button
          variant="ghost"
          icon="chevronRight"
          iconPlacement="end"
          iconSize="sm"
          component={RouterLink}
          to={getSeriesRelationPath(params.row.key)}
          className="ntq-srel-list-enter"
        >
          进入
        </Button>
      ),
    },
  ]), []);

  return (
    <PageLayout
      className="ntq-srel-list-page"
      breadcrumbsItems={[{ label: '高级功能', to: '/advanced/tags' }]}
      breadcrumbsCurrent="序列关系"
      bannerTitle="序列关系"
      bannerDescription="选择一条序列关系场景进行配置与跑批，或新建场景。"
      loading={!pageReady}
      loadingMessage="正在加载序列关系…"
    >
      <Section className="ntq-srel-list-page__stack" gap="md">
        {loadError ? <Message status="error">{loadError}</Message> : null}

        <Section className="ntq-srel-list-grid" gap="md">
          <ListToolbar
            search={(
              <SearchField
                fluid
                surface="glass"
                placeholder="搜索名称或 Key"
                label="搜索序列关系"
                value={nameQuery}
                onChange={(e) => setNameQuery(e.target.value)}
              />
            )}
            actions={(
              <>
                <span data-ntq-help="series-relation-list-refresh">
                  <Button
                    variant="glass"
                    icon="refresh"
                    onClick={load}
                    disabled={loading}
                  >
                    刷新
                  </Button>
                </span>
                <span data-ntq-help="series-relation-list-create">
                  <Button
                    variant="primary"
                    icon="add"
                    onClick={() => {
                      setNewKey('');
                      setNewDisplayName('');
                      setNewOpen(true);
                    }}
                  >
                    新建
                  </Button>
                </span>
              </>
            )}
          />

          <div className="ntq-srel-list-grid-body">
            <DataGrid
              autoHeight
              rows={displayRows}
              columns={columns}
              loading={loading}
              pageSizeOptions={[10, 25, 50]}
              paginationModel={paginationModel}
              onPaginationModelChange={setPaginationModel}
              getRowId={(row) => row.id}
              onRowDoubleClick={(params) => enterScene(params.row.key)}
            />
          </div>
        </Section>
      </Section>

      <Dialog
        open={newOpen}
        onClose={() => setNewOpen(false)}
        title="新建序列关系场景"
        size="sm"
        actions={(
          <>
            <Button variant="ghost" onClick={() => setNewOpen(false)}>取消</Button>
            <Button variant="primary" onClick={confirmNew}>创建</Button>
          </>
        )}
      >
        <Section gap="md">
          <TextField
            label="场景 key"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="如 banks_vs_macro"
            maxWidth={false}
            surface="glass"
            autoFocus
          />
          <TextField
            label="显示名（可选）"
            value={newDisplayName}
            onChange={(e) => setNewDisplayName(e.target.value)}
            maxWidth={false}
            surface="glass"
          />
        </Section>
      </Dialog>
    </PageLayout>
  );
}

export default SeriesRelationListPage;
