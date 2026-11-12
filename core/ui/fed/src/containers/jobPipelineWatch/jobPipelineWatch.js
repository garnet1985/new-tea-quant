import React, { useEffect, useRef } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Link } from '@mui/material';
import { fetchPipelineStatus } from 'api/runtimeApi';
import { showToast } from 'containers/toast';
import { jobDeepLink, jobDisplayName } from 'service/jobPipelineLinks';
import logClientError from 'service/logClientError';

const IDLE_POLL_MS = 4000;
const BUSY_POLL_MS = 1500;
const TOAST_MS = 8000;

/**
 * 壳层静默盯 JobPipeline：有 running 则加快轮询；任务从有变无时 toast + 快捷链。
 * 人已在目标页时不弹（避免与现场进度重复吵）。
 */
function JobPipelineWatch() {
  const location = useLocation();
  const locationRef = useRef(location);
  const watchedRef = useRef(null);
  const timerRef = useRef(0);

  useEffect(() => {
    locationRef.current = location;
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
      if (href && (path === href || path.startsWith(`${href}/`))) {
        return;
      }
      const name = jobDisplayName(prevJob);
      showToast({
        severity: 'success',
        duration: TOAST_MS,
        content: href ? (
          <span>
            {`「${name}」已结束。`}
            {' '}
            <Link component={RouterLink} to={href} underline="hover">
              去查看
            </Link>
          </span>
        ) : (
          `「${name}」已结束。`
        ),
      });
    };

    const tick = async () => {
      if (cancelled) return;
      let nextMs = IDLE_POLL_MS;
      try {
        const st = await fetchPipelineStatus();
        if (cancelled) return;
        const job = st?.job && st.busy ? st.job : null;
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
          nextMs = IDLE_POLL_MS;
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
