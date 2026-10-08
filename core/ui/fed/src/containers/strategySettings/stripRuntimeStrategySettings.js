/**
 * 提交回测前去掉不属于策略设置的调度 / 性能字段。
 * 这些值由引擎自己决定，不写进 settings。
 */

const ENUMERATOR_DISPATCH_KEYS = [
  'max_workers',
  'max_parallel_jobs_cap',
  'is_verbose',
  'memory_budget_mb',
  'memory_floor_mb',
  'main_process_reserve_mb',
  'warmup_batch_size',
  'min_batch_size',
  'max_batch_size',
  'monitor_interval',
  'entities_per_job',
  'entities_per_job_min',
  'entities_per_job_max',
  'dispatch_probe',
  'dispatch_probe_entities',
  'dispatch_probe_safety_factor',
  'mb_per_entity_staged',
  'worker_memory_fraction',
  'prefetch_ahead',
  'max_test_versions',
];

const PRICE_SIMULATOR_DISPATCH_KEYS = [
  'max_workers',
  'max_parallel_jobs_cap',
  'entities_per_job',
  'dispatch_probe',
  'dispatch_probe_entities',
  'dispatch_probe_safety_factor',
  'sec_per_entity_staged',
  'sec_per_job_overhead_staged',
  'force_main_process',
  'start_date',
  'end_date',
  'fees',
];

function stripKeysFromBlock(block, keys) {
  if (!block || typeof block !== 'object') return block;
  const out = { ...block };
  keys.forEach((key) => {
    delete out[key];
  });
  return out;
}

export function stripRuntimeStrategySettings(settings) {
  if (!settings || typeof settings !== 'object') return settings;
  const out = { ...settings };
  delete out.performance;

  if (out.enumerator) {
    out.enumerator = stripKeysFromBlock(out.enumerator, ENUMERATOR_DISPATCH_KEYS);
  }
  if (out.price_simulator) {
    out.price_simulator = stripKeysFromBlock(out.price_simulator, PRICE_SIMULATOR_DISPATCH_KEYS);
  }

  return out;
}
