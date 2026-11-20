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
        title="确认覆盖用户空间"
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
          您已选择“覆盖用户空间”。此操作会删除目标目录中的现有内容，并重新初始化，
          可能覆盖现有策略、标签和用户配置。确定继续吗？
        </p>
      </Dialog>

      <Dialog
        open={dbRiskConfirmOpen}
        onClose={() => setDbRiskConfirmOpen(false)}
        title="确认是否覆盖已有数据"
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
              系统检测到本地数据库目录中已有数据文件。
              继续安装后，导入演示数据可能覆盖其中部分内容，且通常无法撤销。请确认要继续。
            </>
          ) : (
            <>
              系统检测到目标数据库
              {dbRiskContext.dbType || dbRiskContext.database
                ? `（${dbRiskContext.dbType || '数据库'}:${dbRiskContext.database || '未命名'}）`
                : ''}
              已存在。
              继续安装后，导入演示数据可能覆盖其中部分内容，且通常无法撤销。请确认要继续。
            </>
          )}
        </p>
      </Dialog>
    </>
  );
}

export default SetupDialogs;
