import React, { useEffect, useRef } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { fetchPipelineStatus } from 'api/runtimeApi';
import { getImportDataProgress } from 'api/setupApi';
import { showToast } from 'containers/toast';
import { jobDeepLink, jobDisplayName } from 'service/jobPipelineLinks';
import { publishPipelineSnapshot } from 'service/jobPipelineBus';
import { addUnreadJob, dismissUnreadMatchingPath } from 'service/jobPipelineUnread';
import logClientError from 'service/logClientError';

const IDLE_POLL_MS = 4000;
const BUSY_POLL_MS = 1500;
const TOAST_MS = 8000;

/** 导入任务细进度写在 setup/import，管道表可能尚未挂上；用同一数据源补全。 */
async function enrichImportDataProgress(snapshot) {
  const job = snapshot?.job;
  if (!snapshot?.busy || String(job?.kind || '') !== 'import_data') {
    return snapshot;
  }
  if (job?.progress && Number.isFinite(Number(job.progress.percent))) {
    return snapshot;
  }
  try {
    const ip = await getImportDataProgress();
    if (!ip?.running) return snapshot;
    let detail = String(ip.statusText || '').trim();
    if (!detail) {
      if (ip.phase === 'downloading') detail = '数据下载中…';
      else if (ip.phase === 'preparing') detail = '准备导入…';
      else if (ip.totalTables > 0) {
        detail = `正在导入 ${ip.completedCount}/${ip.totalTables}${
          ip.currentTable ? `：${ip.currentTable}` : ''
        }`;
      } else {
        detail = '正在导入数据…';
      }
    }
    const ratio = Math.max(0, Math.min(1, Number(ip.ratio) || 0));
    const progress = {
      ratio,
      percent: Math.round(ratio * 100),
      status: 'running',
      label: '导入数据',
      detail,
    };
    const jobId = String(job.job_id || '');
    const nextJob = { ...job, progress };
    const jobs = Array.isArray(snapshot.jobs)
      ? snapshot.jobs.map((row) => (
        String(row?.job_id || '') === jobId ? { ...row, progress } : row
      ))
      : [nextJob];
    return {
      ...snapshot,
      job: nextJob,
      jobs,
      progress,
    };
  } catch (_err) {
    return snapshot;
  }
}

/**
 * 壳层静默盯 JobPipeline：广播快照；任务从有→无时 toast + 未读完成缓冲。
 * 人已在目标页时仍提示「已结束」（短文案），并自动清未读。
 */
function JobPipelineWatch() {
  const location = useLocation();
  const locationRef = useRef(location);
  const watchedRef = useRef(null);
  const timerRef = useRef(0);

  useEffect(() => {
    locationRef.current = location;
    dismissUnreadMatchingPath(location.pathname);
  }, [location]);

  useEffect(() => {
    let cancelled = false;

    const schedule = (ms) => {
      window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(tick, ms);
    };

    const maybeToastFinished = (prevJob) => {
      if (!prevJob) return;
      const href = jobDeepLink(prevJob);
      const path = String(locationRef.current?.pathname || '');
      const onTarget = Boolean(href) && (path === href || path.startsWith(`${href}/`));
      const name = jobDisplayName(prevJob);
      if (onTarget) {
        dismissUnreadMatchingPath(path);
      } else {
        addUnreadJob(prevJob);
      }
      showToast({
        severity: 'success',
        duration: TOAST_MS,
        content: onTarget
          ? `「${name}」已结束。`
          : (
            <span>
              {`「${name}」已结束。`}
              {' '}
              {href ? (
                <RouterLink className="ntq-link" to={href}>
                  去查看
                </RouterLink>
              ) : null}
            </span>
          ),
      });
    };

    const tick = async () => {
      if (cancelled) return;
      let nextMs = IDLE_POLL_MS;
      try {
        const raw = await fetchPipelineStatus();
        if (cancelled) return;
        const st = await enrichImportDataProgress(raw);
        if (cancelled) return;
        publishPipelineSnapshot(st);
        const job = st?.job && st.busy ? st.job : null;
        const hasPending = Number(st?.pending_count || 0) > 0
          || (Array.isArray(st?.pending) && st.pending.length > 0);
        const prev = watchedRef.current;
        if (job) {
          // 保留完整快照（含 started_at / progress），结束入未读时用来冻结「已运行」。
          watchedRef.current = { ...job, job_id: String(job.job_id || '') };
          nextMs = BUSY_POLL_MS;
        } else {
          if (prev?.job_id) {
            maybeToastFinished({
              ...prev,
              finished_at: prev.finished_at || Date.now(),
            });
          }
          watchedRef.current = null;
          nextMs = hasPending ? BUSY_POLL_MS : IDLE_POLL_MS;
        }
      } catch (error) {
        logClientError('jobPipelineWatch.tick', error);
        nextMs = IDLE_POLL_MS;
      }
      if (!cancelled) schedule(nextMs);
    };

    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timerRef.current);
    };
  }, []);

  return null;
}

export default JobPipelineWatch;
