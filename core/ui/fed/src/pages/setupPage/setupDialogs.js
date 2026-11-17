import React from 'react';
import { Button, Dialog } from 'ui';

function SetupDialogs({
  overwriteConfirmOpen,
  setOverwriteConfirmOpen,
  dbRiskConfirmOpen,
  setDbRiskConfirmOpen,
  dbRiskContext,
  onConfirmOverwrite,
  onConfirmDbRisk,
}) {
  const isDuckdb = Boolean(dbRiskContext.isDuckdb) || dbRiskContext.dbType === 'duckdb';

  return (
    <>
      <Dialog
        open={overwriteConfirmOpen}
        onClose={() => setOverwriteConfirmOpen(false)}
        title="确认覆盖 userspace"
        size="sm"
        actions={(
          <>
            <Button variant="ghost" onClick={() => setOverwriteConfirmOpen(false)}>
              取消
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                setOverwriteConfirmOpen(false);
                onConfirmOverwrite();
              }}
            >
              确认覆盖
            </Button>
          </>
        )}
      >
        <p className="ntq-muted">
          你选择了“覆盖 userspace”。此操作会删除目标目录中的现有内容，并用初始化包重新解压，
          可能覆盖现有策略、标签和用户配置。确定继续吗？
        </p>
      </Dialog>

      <Dialog
        open={dbRiskConfirmOpen}
        onClose={() => setDbRiskConfirmOpen(false)}
        title="确认数据库风险"
        size="sm"
        actions={(
          <>
            <Button variant="ghost" onClick={() => setDbRiskConfirmOpen(false)}>
              返回检查
            </Button>
            <Button
              variant="attention"
              onClick={() => {
                setDbRiskConfirmOpen(false);
                onConfirmDbRisk();
              }}
            >
              我已确认，继续
            </Button>
          </>
        )}
      >
        <p className="ntq-muted">
          {isDuckdb ? (
            <>
              系统检测到
              {' '}
              <strong>userspace/system/db/</strong>
              {' '}
              下已有 DuckDB 数据文件（如 data.duckdb / tag.duckdb / strategy.duckdb）。
              继续执行后，初始化数据导入可能覆盖其中部分表数据。请确认你要继续。
            </>
          ) : (
            <>
              系统检测到目标数据库
              {dbRiskContext.dbType || dbRiskContext.database
                ? `（${dbRiskContext.dbType || 'db'}:${dbRiskContext.database || '未命名'}）`
                : ''}
              已存在。
              继续执行后，初始化数据导入可能覆盖其中部分表数据。请确认你要继续覆盖初始化数据。
            </>
          )}
        </p>
      </Dialog>
    </>
  );
}

export default SetupDialogs;
