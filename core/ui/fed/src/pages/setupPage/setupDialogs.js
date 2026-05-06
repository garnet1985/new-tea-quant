import React from 'react';
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';

function SetupDialogs({
  overwriteConfirmOpen,
  setOverwriteConfirmOpen,
  dbRiskConfirmOpen,
  setDbRiskConfirmOpen,
  dbRiskContext,
  onConfirmOverwrite,
  onConfirmDbRisk,
}) {
  return (
    <>
      <Dialog
        open={overwriteConfirmOpen}
        onClose={() => setOverwriteConfirmOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>确认覆盖 userspace</DialogTitle>
        <DialogContent>
          <DialogContentText>
            你选择了“覆盖 userspace”。此操作会删除目标目录中的现有内容，并用初始化包重新解压，
            可能覆盖现有策略、标签和用户配置。确定继续吗？
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOverwriteConfirmOpen(false)} color="inherit">
            取消
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              setOverwriteConfirmOpen(false);
              onConfirmOverwrite();
            }}
          >
            确认覆盖
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={dbRiskConfirmOpen}
        onClose={() => setDbRiskConfirmOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>确认数据库风险</DialogTitle>
        <DialogContent>
          <DialogContentText>
            系统检测到目标数据库
            {dbRiskContext.dbType || dbRiskContext.database
              ? `（${dbRiskContext.dbType || 'db'}:${dbRiskContext.database || '未命名'}）`
              : ''}已存在。
            继续执行后，初始化数据导入可能覆盖其中部分表数据。请确认你要继续覆盖初始化数据。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDbRiskConfirmOpen(false)} color="inherit">
            返回检查
          </Button>
          <Button
            color="warning"
            variant="contained"
            onClick={() => {
              setDbRiskConfirmOpen(false);
              onConfirmDbRisk();
            }}
          >
            我已确认，继续
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default SetupDialogs;
