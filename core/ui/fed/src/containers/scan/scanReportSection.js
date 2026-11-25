import React from 'react';
import { Button, Heading, Section } from 'ui';
import {
  formatScanDate,
  formatStrategyVersionLabel,
  readWorkbenchVersion,
  SHOW_REPORT_GENERATED_AT,
} from './scanHelpers';

/** 扫描完成后的摘要报告条。 */
export default function ScanReportSection({
  scanTriggeredAt,
  reportGeneratedAt,
  reportStrategyName,
  reportStrategyId,
  reportCount,
  onOpenDetail,
  reportPayload,
  reportDemo,
  enabledPostProcessors,
}) {
  const strategyVersion = formatStrategyVersionLabel(readWorkbenchVersion(reportPayload))
    || String(reportPayload?.strategy_version || reportPayload?.strategyVersion || '').trim();

  return (
    <Section className="scan-section scan-section--report" gap="sm">
      <div className="scan-report__head">
        <Heading level="h3" gap="none">扫描报告</Heading>
        <span className="ntq-muted">
          扫描当日：{scanTriggeredAt || reportGeneratedAt || '—'}
        </span>
        {SHOW_REPORT_GENERATED_AT ? (
          <span className="ntq-muted">报告日期：{reportGeneratedAt || '—'}</span>
        ) : null}
      </div>
      <p className="scan-report__lead">
        使用策略
        {' '}
        <strong>{reportStrategyName || reportStrategyId || '—'}</strong>
        {strategyVersion ? (
          <>
            {' '}
            <span className="ntq-muted">（{strategyVersion}）</span>
          </>
        ) : null}
        {' '}
        扫描完成：共找到
        {' '}
        <Button
          variant="ghost"
          className="scan-report__count"
          disabled={reportCount == null}
          onClick={(e) => {
            e.stopPropagation();
            if (!reportStrategyId || reportCount == null) return;
            onOpenDetail(reportStrategyId);
          }}
        >
          {reportCount == null ? '—' : reportCount}
        </Button>
        {' '}
        个机会
      </p>
      <div className="scan-report__facts ntq-muted">
        <p>- 扫描日期：{formatScanDate(reportPayload?.date) || '—'}</p>
        <p>- 策略版本：{strategyVersion || '—'}</p>
        <p>- 总扫描股票数：{Number(reportPayload?.total_stocks ?? 0) || '—'}</p>
        <p>- 模式：{reportDemo === true ? '演示模式' : '严格模式'}</p>
        <p>
          - 扫描后处理：{(() => {
            if (reportPayload?.post_process?.skipped) return '本次已跳过';
            const ran = Array.isArray(reportPayload?.post_process?.ran)
              ? reportPayload.post_process.ran
              : [];
            const enabled = Array.isArray(reportPayload?.post_process?.enabled)
              ? reportPayload.post_process.enabled
              : enabledPostProcessors.map((row) => row.key);
            if (ran.length) return `已运行 ${ran.join('、')}`;
            if (enabled.length) return '已启用但未回报运行结果（可能失败或跳过）';
            return '未启用';
          })()}
        </p>
      </div>
      <p className="ntq-muted scan-report__hint">请点击表格里的机会数量查看详情。</p>
    </Section>
  );
}
