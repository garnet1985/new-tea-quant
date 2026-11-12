/** 未读完成任务：前端缓冲，看过后从管道坞去掉（非服务端历史）。 */

import { jobDeepLink } from 'service/jobPipelineLinks';

const STORAGE_KEY = 'ntq.jobPipeline.unread';
const listeners = new Set();

function readStore() {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((row) => row && typeof row === 'object') : [];
  } catch (_) {
    return [];
  }
}

function writeStore(rows) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
  } catch (_) {
    /* ignore quota / private mode */
  }
}

let latest = typeof window !== 'undefined' ? readStore() : [];

function emit() {
  listeners.forEach((fn) => {
    try {
      fn(latest);
    } catch (_) {
      /* ignore subscriber errors */
    }
  });
}

function normalizeJob(job) {
  if (!job || typeof job !== 'object') return null;
  const jobId = String(job.job_id || '').trim();
  if (!jobId) return null;
  return {
    job_id: jobId,
    kind: job.kind || null,
    resource_key: job.resource_key || null,
    label: job.label || null,
    status: 'completed',
    finished_at: job.finished_at || Date.now(),
  };
}

export function getUnreadJobs() {
  return latest.slice();
}

export function subscribeUnreadJobs(fn) {
  listeners.add(fn);
  try {
    fn(latest);
  } catch (_) {
    /* ignore */
  }
  return () => {
    listeners.delete(fn);
  };
}

/** 任务结束且尚未查看时入缓冲；同 id 不重复。 */
export function addUnreadJob(job) {
  const row = normalizeJob(job);
  if (!row) return latest.slice();
  if (latest.some((item) => String(item.job_id) === row.job_id)) return latest.slice();
  latest = [row, ...latest].slice(0, 12);
  writeStore(latest);
  emit();
  return latest.slice();
}

export function dismissUnreadJob(jobId) {
  const id = String(jobId || '').trim();
  if (!id) return latest.slice();
  const next = latest.filter((row) => String(row.job_id) !== id);
  if (next.length === latest.length) return latest.slice();
  latest = next;
  writeStore(latest);
  emit();
  return latest.slice();
}

/** 当前路径命中未读任务 deep link 时视为已查看并移除。 */
export function dismissUnreadMatchingPath(pathname) {
  const path = String(pathname || '').trim();
  if (!path || !latest.length) return latest.slice();
  const next = latest.filter((row) => {
    const href = jobDeepLink(row);
    if (!href) return true;
    return !(path === href || path.startsWith(`${href}/`));
  });
  if (next.length === latest.length) return latest.slice();
  latest = next;
  writeStore(latest);
  emit();
  return latest.slice();
}
