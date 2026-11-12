import React, { useEffect, useRef } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Link } from '@mui/material';
import { fetchPipelineStatus } from 'api/runtimeApi';
import { showToast } from 'containers/toast';
import { jobDeepLink, jobDisplayName } from 'service/jobPipelineLinks';
import { publishPipelineSnapshot } from 'service/jobPipelineBus';
import { addUnreadJob, dismissUnreadMatchingPath } from 'service/jobPipelineUnread';
import logClientError from 'service/logClientError';

const IDLE_POLL_MS = 4000;
const BUSY_POLL_MS = 1500;
const TOAST_MS = 8000;

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
                <Link component={RouterLink} to={href} underline="hover">
                  去查看
                </Link>
              ) : null}
            </span>
          ),
      });
    };

    const tick = async () => {
      if (cancelled) return;
      let nextMs = IDLE_POLL_MS;
      try {
        const st = await fetchPipelineStatus();
        if (cancelled) return;
        publishPipelineSnapshot(st);
        const job = st?.job && st.busy ? st.job : null;
        const hasPending = Number(st?.pending_count || 0) > 0
          || (Array.isArray(st?.pending) && st.pending.length > 0);
        const prev = watchedRef.current;
        if (job) {
          watchedRef.current = {
            job_id: String(job.job_id || ''),
            kind: job.kind,
            resource_key: job.resource_key,
            label: job.label,
          };
          nextMs = BUSY_POLL_MS;
        } else {
          if (prev?.job_id) {
            maybeToastFinished(prev);
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
