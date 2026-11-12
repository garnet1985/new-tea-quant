import request, { API_VERSION_PREFIX } from 'service/request';

const API_RUNTIME_PIPELINE = `${API_VERSION_PREFIX}/runtime/pipeline`;

function mapPipelineMessage(m = {}) {
  const job = m.job && typeof m.job === 'object' ? m.job : null;
  const jobs = Array.isArray(m.jobs) ? m.jobs.filter((row) => row && typeof row === 'object') : [];
  const pending = Array.isArray(m.pending)
    ? m.pending.filter((row) => row && typeof row === 'object')
    : jobs.filter((row) => String(row.status || '') === 'pending');
  return {
    busy: Boolean(m.busy) || Boolean(job),
    job,
    jobs,
    pending,
    pending_count: Number.isFinite(Number(m.pending_count))
      ? Number(m.pending_count)
      : pending.length,
    kind: m.kind ?? job?.kind ?? null,
    job_id: m.job_id ?? job?.job_id ?? null,
    resource_key: m.resource_key ?? job?.resource_key ?? null,
    label: m.label ?? job?.label ?? null,
    domains: Array.isArray(m.domains)
      ? m.domains
      : (Array.isArray(job?.domains) ? job.domains : []),
    started_at: m.started_at ?? job?.started_at ?? null,
    status: m.status ?? job?.status ?? null,
    progress: m.progress ?? job?.progress ?? null,
  };
}

/** T1-00：管道任务表（running + pending） */
export async function fetchPipelineStatus() {
  const json = await request.getJson(API_RUNTIME_PIPELINE);
  return mapPipelineMessage(json?.message || {});
}

/** 取消尚未执行的 pending job */
export async function cancelPipelineJob(jobId) {
  const id = String(jobId || '').trim();
  if (!id) throw new Error('缺少 job_id');
  const encoded = id
    .split('/')
    .filter(Boolean)
    .map((seg) => encodeURIComponent(seg))
    .join('/');
  const json = await request.deleteJson(`${API_RUNTIME_PIPELINE}/jobs/${encoded}`);
  const m = json?.message || {};
  return {
    cancelled: Boolean(m.cancelled),
    job_id: String(m.job_id || id),
    reason: String(m.reason || '').trim(),
    pipeline: mapPipelineMessage(m),
  };
}
