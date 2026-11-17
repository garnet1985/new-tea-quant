import React from 'react';
import { Icon, Message } from 'ui';
import { progressRatio } from 'service/progress/ratio';
import './setupExecutionPanel.scss';

function stateIcon(row, runningStep) {
  if (runningStep && row.id === runningStep) {
    return (
      <span className="setup-step-state">
        <Icon name="refresh" size="md" spin />
        <span>执行中...</span>
      </span>
    );
  }
  if (row.state === '已完成') {
    return (
      <span className="setup-step-state">
        <Icon name="success" size="md" tone="success" />
        <span>已完成</span>
      </span>
    );
  }
  if (row.state === '失败') {
    return (
      <span className="setup-step-state">
        <Icon name="cancel" size="md" tone="error" />
        <span>失败</span>
      </span>
    );
  }
  if (row.state === '待输入') {
    return (
      <span className="setup-step-state">
        <Icon name="radioUnchecked" size="md" tone="warning" />
        <span>待输入</span>
      </span>
    );
  }
  return (
    <span className="setup-step-state">
      <Icon name="radioUnchecked" size="md" tone="disabled" />
      <span>{row.state}</span>
    </span>
  );
}

function SetupExecutionPanel({
  flowStage,
  progressText,
  runningStep,
  importProgress,
  pollWarning,
  rows,
}) {
  if (flowStage !== 'executing') return null;

  return (
    <section className="setup-exec-panel">
      <h3 className="setup-exec-panel__title">自动执行步骤</h3>
      <p className="setup-exec-panel__text ntq-muted">{progressText}</p>
      {pollWarning ? (
        <Message status="warning">
          {pollWarning}
        </Message>
      ) : null}
      {runningStep === 'import_data' && importProgress.running ? (
        <Message status="info">
          {importProgress.phase === 'downloading' || importProgress.phase === 'preparing'
            ? (importProgress.statusText
              || (importProgress.phase === 'downloading' ? '数据下载中…' : '准备导入…'))
            : importProgress.totalTables > 0
              ? (
                <>
                  导入进度：{importProgress.completedCount}/{importProgress.totalTables}
                  （{Math.round(progressRatio(importProgress.ratio) * 100)}%）
                  {importProgress.currentTable ? `，当前表：${importProgress.currentTable}` : ''}
                </>
              )
              : '准备导入…'}
        </Message>
      ) : null}
      <div className="setup-page__step-list">
        {rows.map((row) => (
          <div key={row.id} className="setup-page__step-row">
            <span className="setup-page__step-row-index">{row.order}</span>
            <div className="setup-page__step-row-main">
              <p className="setup-page__step-row-name">{row.name}</p>
              <p className="setup-page__step-row-detail ntq-muted">{row.detail}</p>
            </div>
            {stateIcon(row, runningStep)}
          </div>
        ))}
      </div>
    </section>
  );
}

export default SetupExecutionPanel;
