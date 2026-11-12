import request, { API_VERSION_PREFIX } from 'service/request';

const API_RUNTIME_PIPELINE = `${API_VERSION_PREFIX}/runtime/pipeline`;

/**
 * T1-00：当前 running 长任务（JobPipeline）
 * @returns {Promise<{
 *   busy: boolean,
 *   job: object|null,
 *   kind?: string|null,
 *   job_id?: string|null,
 *   label?: string|null,
 *   resource_key?: string|null,
 *   status?: string|null,
 *   progress?: number|null,
 *   started_at?: string|null,
 *   domains?: string[],
 * }>}
 */
export async function fetchPipelineStatus() {
  const json = await request.getJson(API_RUNTIME_PIPELINE);
  const m = json?.message || {};
  const job = m.job && typeof m.job === 'object' ? m.job : null;
  return {
    busy: Boolean(m.busy) || Boolean(job),
    job,
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
